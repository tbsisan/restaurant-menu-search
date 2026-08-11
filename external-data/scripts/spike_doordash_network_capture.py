#!/usr/bin/env python3
"""Spike: intercept DoorDash's in-page network traffic to find item modifier data.

Motivation: DoorDash's store-page JSON-LD (see parse_doordash_jsonld.py) carries
only name/description/price per MenuItem - no modifier groups, no size variants.
Confirmed by grepping a full saved store page: no __NEXT_DATA__, no Apollo cache,
no optionList/extraOptions/minNumOptions anywhere in the HTML. So the modifier
data has to arrive on demand when an item is opened. This script finds out what
request delivers it, so a real scraper can read that response instead of
clicking through every option in the DOM (the expensive path Rezku needs).

Method: monkeypatch window.fetch and XMLHttpRequest *after* page load, so every
subsequent request records {method, url, request body, status, response body}
into window.__netlog. Then click an item and read the log back out.

Subcommands keep one headed tab alive across invocations so the flow can be
driven step by step:

  open    - open the store page under a persistent profile
  record  - install the fetch/XHR recorder into the live page
  probe   - list item-card selector candidates found in the DOM
  click   - click the Nth item card (fires the request we want)
  dump    - write the netlog to disk (summary + full bodies)
  close   - close the tab and session

Requires the camofox-browser server running headed (camofox-startup skill).
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path
from typing import Any

import requests

# Patches fetch + both XHR entry points. Kept idempotent so re-running `record`
# after a soft navigation doesn't double-wrap. Bodies are capped per entry so a
# stray image/HTML response can't blow up the evaluate payload; the cap is high
# enough that a menu-item JSON payload arrives whole.
INSTALL_RECORDER_JS = r"""
(function() {
  if (window.__netlogInstalled) { return JSON.stringify({already: true, count: window.__netlog.length}); }
  window.__netlog = [];
  window.__netlogInstalled = true;
  var CAP = 2000000;

  var origFetch = window.fetch;
  window.fetch = function() {
    var args = arguments;
    var req = args[0];
    var init = args[1] || {};
    var url = (typeof req === 'string') ? req : (req && req.url) || '';
    var method = (init && init.method) || (req && req.method) || 'GET';
    var reqBody = null;
    try { reqBody = (init && init.body) ? String(init.body).slice(0, CAP) : null; } catch (e) {}
    var entry = {kind: 'fetch', method: method, url: url, request_body: reqBody, status: null, response_body: null, error: null, t: Date.now()};
    window.__netlog.push(entry);
    return origFetch.apply(this, args).then(function(resp) {
      entry.status = resp.status;
      try {
        resp.clone().text().then(function(text) { entry.response_body = text.slice(0, CAP); },
                                function(e) { entry.error = 'body read failed: ' + e; });
      } catch (e) { entry.error = 'clone failed: ' + e; }
      return resp;
    }, function(err) { entry.error = String(err); throw err; });
  };

  var origOpen = XMLHttpRequest.prototype.open;
  var origSend = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function(method, url) {
    this.__netlogEntry = {kind: 'xhr', method: method, url: url, request_body: null, status: null, response_body: null, error: null, t: Date.now()};
    return origOpen.apply(this, arguments);
  };
  XMLHttpRequest.prototype.send = function(body) {
    var entry = this.__netlogEntry;
    if (entry) {
      try { entry.request_body = body ? String(body).slice(0, CAP) : null; } catch (e) {}
      window.__netlog.push(entry);
      this.addEventListener('load', function() {
        entry.status = this.status;
        try { entry.response_body = String(this.responseText || '').slice(0, CAP); } catch (e) { entry.error = 'responseText unavailable'; }
      });
      this.addEventListener('error', function() { entry.error = 'xhr error'; });
    }
    return origSend.apply(this, arguments);
  };

  return JSON.stringify({already: false, count: 0});
})()
""".strip()

# Summary view: everything except the bodies, so the list stays readable.
NETLOG_SUMMARY_JS = r"""
JSON.stringify((window.__netlog || []).map(function(e, i) {
  return {
    i: i, kind: e.kind, method: e.method, status: e.status, url: e.url,
    req_len: e.request_body ? e.request_body.length : 0,
    resp_len: e.response_body ? e.response_body.length : 0,
    error: e.error,
  };
}))
""".strip()

NETLOG_FULL_JS = "JSON.stringify(window.__netlog || [])"

# The store menu is a virtualized grid: cards mount/unmount as you scroll, so a
# single querySelectorAll only ever sees a window of ~10. This accumulates into
# a page-level map across repeated scroll steps, keyed by data-item-id, and
# assigns each card its nearest preceding h2 (category headers are h2, item
# names are h3) by DOM position - same technique as the other scrapers here.
COLLECT_STEP_JS = r"""
(function() {
  if (!window.__ddItems) { window.__ddItems = {}; }
  var heads = Array.from(document.querySelectorAll('h2'));
  var cards = Array.from(document.querySelectorAll('[data-testid="MenuItem"]'));
  cards.forEach(function(card) {
    var id = card.getAttribute('data-item-id');
    if (!id) { return; }
    var section = null;
    for (var i = heads.length - 1; i >= 0; i--) {
      var rel = heads[i].compareDocumentPosition(card);
      if (rel & Node.DOCUMENT_POSITION_FOLLOWING) { section = heads[i].textContent.trim(); break; }
    }
    var nameEl = card.querySelector('h3');
    var priceEl = card.querySelector('[data-testid="StoreMenuItemPrice"]');
    window.__ddItems[id] = {
      item_id: id,
      section: section,
      name: nameEl ? nameEl.textContent.trim() : null,
      card_price: priceEl ? priceEl.textContent.trim() : null,
    };
  });
  return JSON.stringify({total: Object.keys(window.__ddItems).length});
})()
""".strip()

COLLECTED_JS = "JSON.stringify(Object.values(window.__ddItems || {}))"

SCROLL_JS = "(function(){window.scrollBy(0, %d); return JSON.stringify({y: window.scrollY, h: document.body.scrollHeight});})()"

# Same-origin fetch of the endpoint the item modal uses. Confirmed live: only
# storeId + itemId matter - the cursorContext blob, consumerId and CSRF token
# the real page sends are all omissible, and no sign-in is needed. The client
# headers are kept because they're what the real app sends.
ITEMPAGE_FETCH_JS = r"""
(async function() {
  var body = %s;
  var r = await fetch('/graphql/itemPage?operation=itemPage', {
    method: 'POST',
    credentials: 'include',
    headers: {
      'content-type': 'application/json',
      'x-experience-id': 'doordash',
      'apollographql-client-name': '@doordash/app-consumer-production-ssr-client',
      'apollographql-client-version': '3.0'
    },
    body: JSON.stringify(body)
  });
  var t = await r.text();
  return JSON.stringify({status: r.status, body: t});
})()
""".strip()

QUERY_PATH = Path(__file__).resolve().parent.parent / "menu-scraping" / "doordash_spike" / "itempage-query.graphql"

# `[data-testid="LAYER-MANAGER-SHEET"]` is a persistent layer *host* - it sits in
# the DOM on every store page whether or not a sheet is showing (confirmed: it's
# present on desktop-width pages that never popped one). So its existence proves
# nothing; what matters is a dismiss button that is actually laid out and
# visible. Checking geometry rather than presence avoids both false positives
# (clicking a button that isn't there) and false negatives.
DISMISS_PROBE_JS = r"""
(function() {
  var sheet = document.querySelector('[data-testid="LAYER-MANAGER-SHEET"]');
  if (!sheet) { return JSON.stringify({visible: false}); }
  var wanted = /^(keep using web|not now|continue in browser)$/i;
  var buttons = Array.from(sheet.querySelectorAll('button'));
  for (var i = 0; i < buttons.length; i++) {
    var b = buttons[i];
    var text = (b.textContent || '').trim();
    if (!wanted.test(text)) { continue; }
    var r = b.getBoundingClientRect();
    var style = window.getComputedStyle(b);
    if (r.width > 0 && r.height > 0 && style.visibility !== 'hidden' && style.display !== 'none') {
      return JSON.stringify({
        visible: true,
        button: text,
        heading: (sheet.innerText || '').trim().split('\n')[0] || null
      });
    }
  }
  return JSON.stringify({visible: false});
})()
""".strip()

# Item cards on the DoorDash store page. DoorDash's markup is class-hashed, so
# this leans on data-anchor-id / testid attributes plus a generic fallback.
PROBE_JS = r"""
(function() {
  var out = {};
  var sels = [
    '[data-anchor-id="MenuItem"]',
    '[data-testid="MenuItem"]',
    '[data-anchor-id="MenuItemDisplayCard"]',
    'div[data-testid^="MenuItem"]',
    'a[href*="?itemId="]',
    'a[href*="/item/"]',
  ];
  sels.forEach(function(s) {
    try { out[s] = document.querySelectorAll(s).length; } catch (e) { out[s] = 'err'; }
  });
  var first = null;
  for (var i = 0; i < sels.length; i++) {
    var els = document.querySelectorAll(sels[i]);
    if (els.length) {
      first = {selector: sels[i], count: els.length,
               sample: Array.from(els).slice(0, 5).map(function(el) {
                 return (el.textContent || '').trim().slice(0, 90);
               })};
      break;
    }
  }
  out.__chosen = first;
  return JSON.stringify(out);
})()
""".strip()


class CamofoxClient:
    def __init__(self, server: str, user_id: str) -> None:
        self.server = server.rstrip("/")
        self.user_id = user_id

    def _post(self, path: str, body: dict[str, Any], timeout: int = 60) -> dict[str, Any]:
        resp = requests.post(f"{self.server}{path}", json={"userId": self.user_id, **body}, timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    def health(self) -> bool:
        try:
            return requests.get(f"{self.server}/health", timeout=5).ok
        except requests.RequestException:
            return False

    def open_tab(self, url: str, lat: float, lon: float, timezone_id: str) -> str:
        resp = requests.post(
            f"{self.server}/tabs",
            json={
                "userId": self.user_id,
                "sessionKey": "default",
                "url": url,
                "locale": "en-US",
                "timezoneId": timezone_id,
                "geolocation": {"latitude": lat, "longitude": lon},
            },
            timeout=90,
        )
        resp.raise_for_status()
        return resp.json()["tabId"]

    def current_tab(self) -> str | None:
        """Per the camofox-startup skill: never trust a tabId carried across
        shell invocations - re-read it from the server each time."""
        try:
            resp = requests.get(f"{self.server}/tabs", params={"userId": self.user_id}, timeout=15)
            resp.raise_for_status()
            tabs = resp.json().get("tabs") or []
            return tabs[0].get("tabId") or tabs[0].get("id") if tabs else None
        except (requests.RequestException, IndexError, KeyError):
            return None

    def wait(self, tab_id: str, timeout_ms: int = 20000) -> None:
        try:
            self._post(f"/tabs/{tab_id}/wait", {"timeout": timeout_ms})
        except requests.RequestException:
            pass

    def evaluate(self, tab_id: str, expression: str, timeout: int = 60) -> Any:
        data = self._post(f"/tabs/{tab_id}/evaluate", {"expression": expression}, timeout=timeout)
        result = data.get("result")
        if isinstance(result, str):
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                return result
        return result

    def click(self, tab_id: str, selector: str) -> bool:
        try:
            self._post(f"/tabs/{tab_id}/click", {"selector": selector})
            return True
        except requests.RequestException as exc:
            print(f"  click failed: {exc}", file=sys.stderr)
            return False

    def wait_for_selector(self, tab_id: str, selector: str, timeout_ms: int = 4000, poll_ms: int = 300) -> bool:
        deadline = time.monotonic() + timeout_ms / 1000
        check_js = f"!!document.querySelector({json.dumps(selector)})"
        while time.monotonic() < deadline:
            if self.evaluate(tab_id, check_js):
                return True
            time.sleep(poll_ms / 1000)
        return False

    def close_tab(self, tab_id: str) -> None:
        try:
            requests.delete(f"{self.server}/tabs/{tab_id}", params={"userId": self.user_id}, timeout=10)
        except requests.RequestException:
            pass

    def close_session(self) -> None:
        try:
            requests.delete(f"{self.server}/sessions/{self.user_id}", timeout=10)
        except requests.RequestException:
            pass


def human_delay(min_s: float = 0.9, max_s: float = 2.2) -> None:
    time.sleep(random.uniform(min_s, max_s))


class TabLost(RuntimeError):
    """The tab or browser died mid-request; the item itself may be fine."""


class Pacer:
    """Human-ish pacing for a long harvest.

    A uniform 0.9-2.2s gap before every request is itself a fingerprint: real
    inter-action gaps are heavy-tailed, not boxed. This draws from a log-normal
    body (most actions quick) with two kinds of interruption layered on -
    occasional short distractions, and rarer long breaks - so the distribution
    has the shape a person browsing a menu actually produces.

    `--pacing fast` restores the old flat behaviour for quick spot checks.
    """

    def __init__(self, mode: str = "human") -> None:
        self.mode = mode
        self.count = 0
        self.next_break = random.randint(12, 22)
        self.total_slept = 0.0

    def wait(self) -> float:
        if self.mode == "fast":
            delay = random.uniform(0.9, 2.2)
            time.sleep(delay)
            self.total_slept += delay
            return delay

        self.count += 1
        if self.count >= self.next_break:
            # Stepped away - refilled a drink, answered a message.
            delay = random.uniform(45, 130)
            self.next_break = self.count + random.randint(12, 22)
        else:
            roll = random.random()
            if roll < 0.06:
                delay = random.uniform(12, 40)   # reading an item properly
            elif roll < 0.22:
                delay = random.uniform(4.0, 9.0)  # brief consideration
            else:
                delay = min(random.lognormvariate(0.6, 0.55), 7.0)  # scanning
        time.sleep(delay)
        self.total_slept += delay
        return delay


def require_tab(client: CamofoxClient) -> str:
    tab_id = client.current_tab()
    if not tab_id:
        print(f"No open tab for user {client.user_id!r}. Run `open` first.", file=sys.stderr)
        sys.exit(2)
    return tab_id


def cmd_open(client: CamofoxClient, args: argparse.Namespace) -> None:
    tab_id = client.open_tab(args.url, args.latitude, args.longitude, args.timezone)
    client.wait(tab_id, timeout_ms=25000)
    time.sleep(3)
    dismissed = dismiss_interstitials(client, tab_id)
    final_url = client.evaluate(tab_id, "location.href")
    title = client.evaluate(tab_id, "document.title")
    print(f"tab={tab_id}\nurl={final_url}\ntitle={title}")
    if dismissed:
        print(f"dismissed: {dismissed!r}")


def cmd_record(client: CamofoxClient, args: argparse.Namespace) -> None:
    tab_id = require_tab(client)
    print(json.dumps(client.evaluate(tab_id, INSTALL_RECORDER_JS), indent=2))


def cmd_probe(client: CamofoxClient, args: argparse.Namespace) -> None:
    tab_id = require_tab(client)
    print(json.dumps(client.evaluate(tab_id, PROBE_JS), indent=2))


def cmd_click(client: CamofoxClient, args: argparse.Namespace) -> None:
    tab_id = require_tab(client)
    human_delay()
    ok = client.click(tab_id, args.selector)
    print(f"clicked={ok} selector={args.selector}")
    time.sleep(args.settle)
    print(f"url={client.evaluate(tab_id, 'location.href')}")


def cmd_dump(client: CamofoxClient, args: argparse.Namespace) -> None:
    tab_id = require_tab(client)
    summary = client.evaluate(tab_id, NETLOG_SUMMARY_JS) or []
    print(f"{len(summary)} recorded requests")
    for entry in summary:
        print(f"  [{entry['i']:>3}] {entry['kind']:<5} {str(entry['status']):<4} "
              f"resp={entry['resp_len']:<8} {entry['url'][:140]}")
    if args.output:
        full = client.evaluate(tab_id, NETLOG_FULL_JS, timeout=180) or []
        args.output.write_text(json.dumps(full, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nWrote {args.output} ({len(full)} entries)")


def dismiss_interstitials(client: CamofoxClient, tab_id: str) -> str | None:
    """Dismiss DoorDash's "Browse <store> in app" install sheet.

    Confirmed on Jet's Pizza: camofox randomizes screen/viewport per profile, and
    a narrow one (720px wide here) puts DoorDash into its mobile-web layout,
    which pops an app-install sheet over the menu. Left up, it blocks the
    virtualized grid from mounting and `items` collects zero.

    The sheet offers "Keep using web" - clicked here rather than removing the
    node or pressing Escape, both because it's what a person would do and
    because DoorDash records the choice, so it stops reappearing in the profile.
    Best-effort: returns None when no sheet is present, which is the common case
    on desktop-width profiles.
    """
    found = client.evaluate(tab_id, DISMISS_PROBE_JS)
    if not isinstance(found, dict) or not found.get("visible"):
        return None
    human_delay(1.2, 2.8)  # a person reads the sheet before dismissing it
    selector = f'[data-testid="LAYER-MANAGER-SHEET"] button:has-text("{found["button"]}")'
    if not client.click(tab_id, selector):
        return None
    time.sleep(1.5)
    return found.get("heading") or "app-install sheet"


def collect_items(client: CamofoxClient, tab_id: str, max_scrolls: int = 60) -> list[dict[str, Any]]:
    """Scroll the virtualized menu grid end to end, accumulating item cards."""
    dismiss_interstitials(client, tab_id)
    client.evaluate(tab_id, "window.scrollTo(0, 0); null")
    time.sleep(1.0)
    stable = 0
    last_total = 0
    for _ in range(max_scrolls):
        step = client.evaluate(tab_id, COLLECT_STEP_JS) or {}
        total = step.get("total", 0)
        pos = client.evaluate(tab_id, SCROLL_JS % 700) or {}
        time.sleep(random.uniform(0.45, 0.9))
        if total == last_total:
            stable += 1
            if stable >= 4 and pos.get("y", 0) + 1600 >= pos.get("h", 0):
                break
        else:
            stable = 0
        last_total = total
    client.evaluate(tab_id, COLLECT_STEP_JS)
    return client.evaluate(tab_id, COLLECTED_JS, timeout=120) or []


def write_harvest(path: Path, store_url: str, store_id: str, results: list[dict[str, Any]], complete: bool) -> None:
    """Checkpoint. Called periodically during the run, not just at the end - a
    143-item harvest is ~25 minutes and the browser has been observed dying
    mid-run (see recover_tab), which previously discarded every completed
    fetch."""
    ordered = sorted(results, key=lambda r: r.get("menu_position", 0))
    path.write_text(
        json.dumps(
            {"source_url": store_url, "store_id": store_id, "complete": complete, "items": ordered},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def load_previous(path: Path) -> dict[str, dict[str, Any]]:
    """Completed items from an earlier run, keyed by item id, so an interrupted
    harvest resumes instead of re-fetching what it already has."""
    if not path.exists():
        return {}
    try:
        doc = json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}
    return {
        item["item_id"]: item
        for item in doc.get("items") or []
        if item.get("item_id") and item.get("item_page")
    }


def recover_tab(client: CamofoxClient, store_url: str, lat: float, lon: float, tz: str) -> str | None:
    """Re-open the store page after the tab (or the whole browser) goes away.

    Confirmed failure mode: mid-harvest the camofox browser exited entirely -
    `browserConnected: false`, zero camoufox processes, and every subsequent
    /evaluate returned 404. Reopening under the same profile restores cookies
    and the session, so the harvest can carry on.
    """
    existing = client.current_tab()
    if existing:
        return existing
    print("  tab gone - reopening store page", file=sys.stderr)
    try:
        tab_id = client.open_tab(store_url, lat, lon, tz)
    except requests.RequestException as exc:
        print(f"  reopen failed: {exc}", file=sys.stderr)
        return None
    client.wait(tab_id, timeout_ms=25000)
    time.sleep(3)
    dismiss_interstitials(client, tab_id)
    return tab_id


def fetch_item_page(client: CamofoxClient, tab_id: str, store_id: str, item_id: str, query: str) -> dict[str, Any] | None:
    payload = {
        "operationName": "itemPage",
        "variables": {
            "itemId": item_id,
            "consumerId": None,
            "storeId": store_id,
            "isMerchantPreview": False,
            "isNested": False,
            "shouldFetchPresetCarousels": False,
            "fulfillmentType": "Delivery",
            "shouldFetchStoreLiteData": False,
        },
        "query": query,
    }
    try:
        result = client.evaluate(tab_id, ITEMPAGE_FETCH_JS % json.dumps(payload), timeout=120)
    except requests.RequestException as exc:
        # Signals a dead tab/browser rather than a bad item - re-raised as a
        # sentinel so the caller can attempt recovery and retry this item.
        raise TabLost(str(exc)) from exc
    if not isinstance(result, dict) or result.get("status") != 200:
        return None
    try:
        return json.loads(result["body"])
    except (json.JSONDecodeError, KeyError):
        return None


def cmd_items(client: CamofoxClient, args: argparse.Namespace) -> None:
    tab_id = require_tab(client)
    items = collect_items(client, tab_id)
    sections = {}
    for it in items:
        sections.setdefault(it.get("section") or "?", 0)
        sections[it["section"] or "?"] += 1
    print(f"{len(items)} items across {len(sections)} sections")
    for name, count in sections.items():
        print(f"  {count:>3}  {name}")
    if args.output:
        args.output.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Wrote {args.output}")


def cmd_harvest(client: CamofoxClient, args: argparse.Namespace) -> None:
    tab_id = require_tab(client)
    if not QUERY_PATH.exists():
        print(f"Missing GraphQL query at {QUERY_PATH} (captured from a traced item click).", file=sys.stderr)
        sys.exit(2)
    query = QUERY_PATH.read_text()

    store_id = args.store_id
    items = collect_items(client, tab_id)
    if args.limit:
        items = items[: args.limit]

    # Menu order is recorded so output stays stable, but the *fetch* order is
    # shuffled: walking a menu strictly top-to-bottom is a machine tell, and it
    # also makes each session's request sequence identical for a given store.
    for position, item in enumerate(items):
        item["menu_position"] = position
    fetch_order = list(items)
    if args.pacing != "fast":
        random.shuffle(fetch_order)

    pacer = Pacer(args.pacing)
    store_url = client.evaluate(tab_id, "location.href") or args.url or ""
    previous = load_previous(args.output) if args.resume else {}
    if previous:
        print(f"Resuming: {len(previous)} items already captured in {args.output}")
        fetch_order = [i for i in fetch_order if i["item_id"] not in previous]
    print(f"Harvesting optionLists for {len(fetch_order)} items (store {store_id}, pacing={args.pacing})")

    results = list(previous.values())
    failures = 0
    for i, item in enumerate(fetch_order, 1):
        slept = pacer.wait()
        page = None
        for attempt in (1, 2):
            try:
                data = fetch_item_page(client, tab_id, store_id, item["item_id"], query)
                page = ((data or {}).get("data") or {}).get("itemPage")
                break
            except TabLost as exc:
                print(f"  [{i}/{len(fetch_order)}] tab lost ({exc}); attempt {attempt}", file=sys.stderr)
                write_harvest(args.output, store_url, store_id, results, complete=False)
                recovered = recover_tab(client, store_url, args.latitude, args.longitude, args.timezone)
                if not recovered:
                    print("  could not recover browser - stopping early; rerun to resume", file=sys.stderr)
                    write_harvest(args.output, store_url, store_id, results, complete=False)
                    print(f"\nWrote {args.output} ({len(results)} items captured, INCOMPLETE)")
                    return
                tab_id = recovered
        if page is None:
            failures += 1
            print(f"  [{i}/{len(fetch_order)}] FAILED {item['name']!r} ({item['item_id']})")
            results.append({**item, "item_page": None, "error": "no itemPage in response"})
            continue
        groups = page.get("optionLists") or []
        required = sum(1 for g in groups if not g.get("isOptional"))
        nested = sum(1 for g in groups for o in g.get("options") or [] if o.get("nestedExtrasList"))
        nested_note = f" +{nested} nested" if nested else ""
        print(f"  [{i}/{len(items)}] {slept:>5.1f}s  {item['name'][:38]:<38} "
              f"{len(groups)} groups ({required} req){nested_note}")
        results.append({**item, "item_page": page})
        if i % 10 == 0:
            write_harvest(args.output, store_url, store_id, results, complete=False)

    results.sort(key=lambda r: r.get("menu_position", 0))
    print(f"  elapsed in deliberate pauses: {pacer.total_slept/60:.1f} min")

    write_harvest(args.output, store_url, store_id, results, complete=True)
    print(f"\nWrote {args.output} ({len(results)} items, {failures} failures)")


def cmd_close(client: CamofoxClient, args: argparse.Namespace) -> None:
    tab_id = client.current_tab()
    if tab_id:
        client.close_tab(tab_id)
    client.close_session()
    print("closed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--server", default="http://localhost:9377")
    parser.add_argument("--user", default="dd-network-spike", help="camofox-browser profile id")
    sub = parser.add_subparsers(dest="command", required=True)

    p_open = sub.add_parser("open")
    p_open.add_argument("url")
    p_open.add_argument("--latitude", type=float, default=42.1414)
    p_open.add_argument("--longitude", type=float, default=-83.196733)
    p_open.add_argument("--timezone", default="America/Detroit")
    p_open.set_defaults(func=cmd_open)

    sub.add_parser("record").set_defaults(func=cmd_record)
    sub.add_parser("probe").set_defaults(func=cmd_probe)

    p_click = sub.add_parser("click")
    p_click.add_argument("selector")
    p_click.add_argument("--settle", type=float, default=3.0)
    p_click.set_defaults(func=cmd_click)

    p_dump = sub.add_parser("dump")
    p_dump.add_argument("--output", type=Path)
    p_dump.set_defaults(func=cmd_dump)

    p_items = sub.add_parser("items")
    p_items.add_argument("--output", type=Path)
    p_items.set_defaults(func=cmd_items)

    p_harvest = sub.add_parser("harvest")
    p_harvest.add_argument("store_id", help="numeric DoorDash store id, e.g. 2702259")
    p_harvest.add_argument("output", type=Path)
    p_harvest.add_argument("--limit", type=int, default=0, help="stop after N items (0 = all)")
    p_harvest.add_argument("--resume", action="store_true", default=True,
                           help="skip items already present in the output file (default on)")
    p_harvest.add_argument("--no-resume", dest="resume", action="store_false")
    p_harvest.add_argument("--url", default=None, help="store URL used to reopen the tab after a browser crash")
    p_harvest.add_argument("--latitude", type=float, default=42.197513)
    p_harvest.add_argument("--longitude", type=float, default=-83.269677)
    p_harvest.add_argument("--timezone", default="America/Detroit")
    p_harvest.add_argument("--pacing", choices=("human", "fast"), default="human",
                           help="'human' = heavy-tailed gaps, periodic breaks, shuffled fetch order")
    p_harvest.set_defaults(func=cmd_harvest)

    sub.add_parser("close").set_defaults(func=cmd_close)

    args = parser.parse_args()
    client = CamofoxClient(args.server, args.user)
    if not client.health():
        print(f"camofox-browser server not reachable at {args.server}.", file=sys.stderr)
        sys.exit(2)
    args.func(client, args)


if __name__ == "__main__":
    main()
