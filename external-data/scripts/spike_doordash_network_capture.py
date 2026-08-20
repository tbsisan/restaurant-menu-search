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
from typing import Any, Callable
from urllib.parse import urlsplit, urlunsplit

import requests

MENU_CARD_SELECTORS = (
    '[data-anchor-id="MenuItem"]',
    '[data-testid="MenuItem"]',
    '[data-anchor-id="MenuItemDisplayCard"]',
    'div[data-testid^="MenuItem"]',
    'a[href*="?itemId="]',
    'a[href*="/item/"]',
)
MENU_CARD_SELECTORS_JS = json.dumps(MENU_CARD_SELECTORS)
MAX_ITEM_PAGE_CAPTURE_ATTEMPTS = 2

# Patches fetch + both XHR entry points. Kept idempotent so re-running `record`
# after a soft navigation doesn't double-wrap. Bodies are capped per entry so a
# stray image/HTML response can't blow up the evaluate payload; the cap is high
# enough that a menu-item JSON payload arrives whole.
INSTALL_RECORDER_JS = r"""
(function() {
  if (window.__netlogInstalled) {
    // A new manual `record` command begins a new diagnostic session; retain
    // wrappers but never carry an earlier page's entries into its dump.
    window.__netlog = [];
    window.__netlogMeta = {url: location.href, reset_at: Date.now()};
    return JSON.stringify({already: true, reset: true, count: 0});
  }
  window.__netlog = [];
  window.__netlogInstalled = true;
  window.__netlogMeta = {url: location.href, reset_at: Date.now()};
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
# single querySelectorAll only ever sees a window of ~10. The same selector
# contract powers `probe`, page readiness, and collection. Collection is bound
# to the URL present at reset time so manual commands cannot silently combine
# cards from a prior soft navigation with the current store.
RESET_COLLECTION_JS = r"""
(function() {
  window.__ddItems = {};
  window.__ddCollectionMeta = {url: location.href, reset_at: Date.now()};
  return JSON.stringify({url: location.href, reset: true});
})()
""".strip()

COLLECT_STEP_JS = r"""
(function() {
  var selectors = __MENU_CARD_SELECTORS__;
  if (!window.__ddItems || !window.__ddCollectionMeta) {
    return JSON.stringify({error: 'collection_state_not_initialized'});
  }
  if (window.__ddCollectionMeta.url !== location.href) {
    return JSON.stringify({error: 'collection_state_url_mismatch', collection_url: window.__ddCollectionMeta.url, page_url: location.href});
  }
  function itemId(card) {
    var id = card.getAttribute('data-item-id');
    if (id) { return id; }
    var link = card.matches && card.matches('a[href]') ? card : card.querySelector('a[href]');
    if (!link) { return null; }
    try { return new URL(link.href, location.href).searchParams.get('itemId'); } catch (e) { return null; }
  }
  var selectorCounts = {};
  var cardById = {};
  selectors.forEach(function(selector) {
    var eligible = 0;
    Array.from(document.querySelectorAll(selector)).forEach(function(card) {
      var id = itemId(card);
      if (!id) { return; }
      eligible += 1;
      if (!cardById[id]) { cardById[id] = card; }
    });
    selectorCounts[selector] = eligible;
  });
  var heads = Array.from(document.querySelectorAll('h2'));
  Object.keys(cardById).forEach(function(id) {
    var card = cardById[id];
    if (!id) { return; }
    var section = null;
    for (var i = heads.length - 1; i >= 0; i--) {
      var rel = heads[i].compareDocumentPosition(card);
      if (rel & Node.DOCUMENT_POSITION_FOLLOWING) { section = heads[i].textContent.trim(); break; }
    }
    var nameEl = card.querySelector('h3');
    var priceEl = card.querySelector('[data-testid="StoreMenuItemPrice"]');
    // DoorDash displays item sentiment as e.g. "92% (48)" on cards that
    // have enough ratings. Keep it independent from the itemPage response,
    // which supplies modifiers but not card-level popularity data.
    var cardText = (card.innerText || '').replace(/\s+/g, ' ').trim();
    var ratingMatch = cardText.match(/\b(\d{1,3})%\s*\((\d[\d,]*)\)/);
    // The same item can appear in a canonical category and a recommendation
    // shelf.  A virtualized revisit must add membership, not overwrite the
    // category with whichever card mounted last.  `section` remains only as a
    // backward-compatible first-observed value; consumers use `sections`.
    var existing = window.__ddItems[id] || {item_id: id, section: null, sections: []};
    if (!Array.isArray(existing.sections)) {
      existing.sections = existing.section ? [existing.section] : [];
    }
    if (section && existing.sections.indexOf(section) === -1) {
      existing.sections.push(section);
    }
    existing.section = existing.section || section;
    existing.name = existing.name || (nameEl ? nameEl.textContent.trim() : null);
    existing.card_price = existing.card_price || (priceEl ? priceEl.textContent.trim() : null);
    existing.like_percent = existing.like_percent == null && ratingMatch ? Number(ratingMatch[1]) : existing.like_percent;
    existing.like_review_count = existing.like_review_count == null && ratingMatch
      ? Number(ratingMatch[2].replace(/,/g, '')) : existing.like_review_count;
    window.__ddItems[id] = existing;
  });
  return JSON.stringify({
    total: Object.keys(window.__ddItems).length,
    eligible_cards_in_view: Object.keys(cardById).length,
    selector_counts: selectorCounts,
    collection_url: window.__ddCollectionMeta.url
  });
})()
""".replace("__MENU_CARD_SELECTORS__", MENU_CARD_SELECTORS_JS).strip()

COLLECTED_JS = "JSON.stringify(Object.values(window.__ddItems || {}))"

SCROLL_JS = """(function(){
  window.scrollBy(0, %d);
  var h = document.documentElement.scrollHeight || document.body.scrollHeight || 0;
  var viewport = window.innerHeight || 0;
  var y = window.scrollY || window.pageYOffset || 0;
  return JSON.stringify({y: y, h: h, viewport: viewport, at_bottom: y + viewport >= h - 2});
})()"""

# Keep discovery evidence compact.  This deliberately records only counts,
# headings, and high-confidence problem phrases rather than dumping page text
# into every raw menu artifact.  A non-empty menu is the strongest usable-page
# signal; an empty page is never promoted to success merely because the DOM has
# finished loading.
DISCOVERY_PAGE_STATE_JS = r"""
(function() {
  var selectors = __MENU_CARD_SELECTORS__;
  function itemId(card) {
    var id = card.getAttribute('data-item-id');
    if (id) { return id; }
    var link = card.matches && card.matches('a[href]') ? card : card.querySelector('a[href]');
    if (!link) { return null; }
    try { return new URL(link.href, location.href).searchParams.get('itemId'); } catch (e) { return null; }
  }
  var cardById = {};
  Array.from(document.querySelectorAll(selectors.join(','))).forEach(function(card) {
    var id = itemId(card);
    if (id && !cardById[id]) { cardById[id] = card; }
  });
  var cards = Object.keys(cardById).map(function(id) { return cardById[id]; });
  var visibleCards = cards.filter(function(el) {
    var rect = el.getBoundingClientRect();
    var style = window.getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
  });
  var headings = Array.from(document.querySelectorAll('h2')).map(function(el) {
    return (el.textContent || '').replace(/\s+/g, ' ').trim();
  }).filter(Boolean);
  var text = ((document.body && document.body.innerText) || '').replace(/\s+/g, ' ').toLowerCase();
  var phrases = [
    'something went wrong',
    'access denied',
    'verify you are human',
    'this store is not available',
    'this store is currently unavailable',
    'this store is closed'
  ];
  var problems = phrases.filter(function(phrase) { return text.indexOf(phrase) !== -1; });
  return JSON.stringify({
    ready_state: document.readyState,
    rendered_menu_card_count: cards.length,
    visible_menu_card_count: visibleCards.length,
    category_headings: Array.from(new Set(headings)).slice(0, 100),
    problem_signals: problems,
    url: location.href,
    title: document.title
  });
})()
""".replace("__MENU_CARD_SELECTORS__", MENU_CARD_SELECTORS_JS).strip()

# Same-origin fetch of the endpoint the item modal uses. Confirmed live: only
# storeId + itemId matter - the cursorContext blob, consumerId and CSRF token
# the real page sends are all omissible, and no sign-in is needed. The client
# headers are kept because they're what the real app sends.
ITEMPAGE_FETCH_JS = r"""
(async function() {
  var body = %s;
  try {
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
    return JSON.stringify({
      status: r.status,
      status_text: r.statusText,
      content_type: r.headers.get('content-type'),
      body: t
    });
  } catch (error) {
    return JSON.stringify({fetch_error: String(error)});
  }
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
  var sels = __MENU_CARD_SELECTORS__;
  function itemId(card) {
    var id = card.getAttribute('data-item-id');
    if (id) { return id; }
    var link = card.matches && card.matches('a[href]') ? card : card.querySelector('a[href]');
    if (!link) { return null; }
    try { return new URL(link.href, location.href).searchParams.get('itemId'); } catch (e) { return null; }
  }
  sels.forEach(function(s) {
    try {
      var matches = Array.from(document.querySelectorAll(s));
      out[s] = {
        matching_nodes: matches.length,
        eligible_items: matches.filter(function(el) { return !!itemId(el); }).length
      };
    } catch (e) { out[s] = {error: String(e)}; }
  });
  var first = null;
  for (var i = 0; i < sels.length; i++) {
    var els = Array.from(document.querySelectorAll(sels[i])).filter(function(el) { return !!itemId(el); });
    if (els.length) {
      first = {selector: sels[i], eligible_items: els.length,
               sample: els.slice(0, 5).map(function(el) {
                 return (el.textContent || '').trim().slice(0, 90);
               })};
      break;
    }
  }
  out.__chosen = first;
  return JSON.stringify(out);
})()
""".replace("__MENU_CARD_SELECTORS__", MENU_CARD_SELECTORS_JS).strip()


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


def write_json_checkpoint(path: Path, payload: Any) -> None:
    """Durably replace a small JSON checkpoint without leaving partial JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def discovery_page_state(client: CamofoxClient, tab_id: str) -> dict[str, Any]:
    """Get compact evidence about whether the rendered page is menu-usable."""
    state = client.evaluate(tab_id, DISCOVERY_PAGE_STATE_JS) or {}
    if not isinstance(state, dict):
        return {
            "ready_state": "unknown",
            "rendered_menu_card_count": 0,
            "visible_menu_card_count": 0,
            "category_headings": [],
            "problem_signals": ["discovery_page_state_unavailable"],
        }
    return state


def wait_for_initial_menu_render(
    client: CamofoxClient,
    tab_id: str,
    timeout_s: float = 12.0,
    poll_s: float = 0.4,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Wait briefly for hydration without treating a ready zero-card DOM as success."""
    started = time.monotonic()
    polls = 0
    latest = discovery_page_state(client, tab_id)
    while True:
        polls += 1
        if latest.get("rendered_menu_card_count", 0) > 0:
            outcome = "menu_cards_rendered"
            break
        if latest.get("problem_signals"):
            outcome = "page_problem_signaled"
            break
        if time.monotonic() - started >= timeout_s:
            outcome = "timed_out_without_menu_cards"
            break
        time.sleep(poll_s)
        latest = discovery_page_state(client, tab_id)
    return latest, {
        "outcome": outcome,
        "waited_ms": round((time.monotonic() - started) * 1000),
        "polls": polls,
    }


def item_section_memberships(item: dict[str, Any]) -> list[str]:
    """Return every observed category for an item, retaining legacy artifacts."""
    raw = item.get("sections")
    values = raw if isinstance(raw, list) else [raw] if isinstance(raw, str) else []
    memberships: list[str] = []
    for value in values:
        if isinstance(value, str) and value.strip() and value.strip() not in memberships:
            memberships.append(value.strip())
    legacy = item.get("section")
    if isinstance(legacy, str) and legacy.strip() and legacy.strip() not in memberships:
        memberships.append(legacy.strip())
    return memberships or ["?"]


def summarize_discovery(
    *,
    items: list[dict[str, Any]],
    initial_page: dict[str, Any],
    final_page: dict[str, Any],
    initial_wait: dict[str, Any],
    stop_reason: str,
    scrolls_attempted: int,
    max_scrolls: int,
    scroll_trace: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a small, inspectable discovery record for the harvest artifact."""
    sections: dict[str, int] = {}
    for item in items:
        for section in item_section_memberships(item):
            sections[section] = sections.get(section, 0) + 1

    problems = list(dict.fromkeys(
        (initial_page.get("problem_signals") or []) + (final_page.get("problem_signals") or [])
    ))
    if not items:
        if problems:
            stop_reason = "page_problem_signaled"
        elif stop_reason in {"bottom_stable", "scroll_limit_reached"}:
            stop_reason = "no_menu_items_observed"
        status = "incomplete"
        page_usable = "no" if problems else "unknown"
    elif stop_reason == "bottom_stable":
        status = "complete"
        page_usable = "yes"
    else:
        status = "incomplete"
        page_usable = "yes"

    return {
        "source": "live_virtualized_scroll",
        "status": status,
        "stop_reason": stop_reason,
        "page_usable": page_usable,
        "initial_wait": initial_wait,
        "initial_page": initial_page,
        "final_page": final_page,
        "problem_signals": problems,
        "scrolls_attempted": scrolls_attempted,
        "max_scrolls": max_scrolls,
        "observed_item_count": len(items),
        "observed_sections": sections,
        "scroll_trace": scroll_trace,
    }


def collect_items(
    client: CamofoxClient,
    tab_id: str,
    max_scrolls: int = 60,
    checkpoint_path: Path | None = None,
    checkpoint_callback: Callable[[list[dict[str, Any]]], None] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Scroll the virtualized menu grid end to end, accumulating item cards.

    The returned discovery record is saved with a harvest so a consumer can
    inspect page readiness, observed categories, each scroll step, and whether
    collection reached a stable bottom rather than merely hitting its cap.
    """
    items: list[dict[str, Any]] = []
    initial_page: dict[str, Any] = {
        "ready_state": "unknown",
        "rendered_menu_card_count": 0,
        "visible_menu_card_count": 0,
        "category_headings": [],
        "problem_signals": [],
    }
    final_page = initial_page
    initial_wait: dict[str, Any] = {"outcome": "not_started", "waited_ms": 0, "polls": 0}
    scrolls_attempted = 0
    scroll_trace: list[dict[str, Any]] = []
    collection_url: str | None = None

    def checkpoint_observed_items(*, force: bool = False) -> None:
        """Persist the current in-memory collection, including an empty loss case."""
        if not force and not items:
            return
        if checkpoint_path:
            write_json_checkpoint(checkpoint_path, items)
        if checkpoint_callback:
            checkpoint_callback(items)

    try:
        dismiss_interstitials(client, tab_id)
        initial_page, initial_wait = wait_for_initial_menu_render(client, tab_id)
        final_page = initial_page
        if initial_wait["outcome"] == "page_problem_signaled":
            return [], summarize_discovery(
                items=[],
                initial_page=initial_page,
                final_page=initial_page,
                initial_wait=initial_wait,
                stop_reason="page_problem_signaled",
                scrolls_attempted=0,
                max_scrolls=max_scrolls,
                scroll_trace=[],
            )

        reset = client.evaluate(tab_id, RESET_COLLECTION_JS) or {}
        if not isinstance(reset, dict) or not isinstance(reset.get("url"), str):
            return [], summarize_discovery(
                items=[],
                initial_page=initial_page,
                final_page=discovery_page_state(client, tab_id),
                initial_wait=initial_wait,
                stop_reason="collection_state_reset_failed",
                scrolls_attempted=0,
                max_scrolls=max_scrolls,
                scroll_trace=[],
            )
        collection_url = reset["url"]

        client.evaluate(tab_id, "window.scrollTo(0, 0); null")
        time.sleep(1.0)
        stable = 0
        last_total = 0
        stop_reason = "scroll_limit_reached"
        for scrolls_attempted in range(1, max_scrolls + 1):
            step = client.evaluate(tab_id, COLLECT_STEP_JS) or {}
            if isinstance(step, dict) and step.get("error"):
                stop_reason = str(step["error"])
                break
            if not isinstance(step, dict) or not isinstance(step.get("total"), int):
                stop_reason = "collection_step_invalid"
                break
            total = step["total"]
            if total != last_total:
                # Card data includes DoorDash's per-item like percentage/count.
                # Read it once, keep it in memory, then checkpoint that exact
                # snapshot so a subsequent browser loss cannot erase it.
                collected = client.evaluate(tab_id, COLLECTED_JS, timeout=120) or []
                if not isinstance(collected, list):
                    stop_reason = "collected_items_unavailable"
                    break
                items = collected
                checkpoint_observed_items()
            pos = client.evaluate(tab_id, SCROLL_JS % 700) or {}
            if not isinstance(pos, dict):
                stop_reason = "scroll_state_unavailable"
                break
            at_bottom = bool(pos.get("at_bottom"))
            scroll_trace.append({
                "step": scrolls_attempted,
                "observed_item_count": total,
                "new_items_since_previous_step": max(total - last_total, 0),
                "scroll_y": pos.get("y"),
                "scroll_height": pos.get("h"),
                "viewport_height": pos.get("viewport"),
                "at_bottom": at_bottom,
                "stable_steps": stable,
                "eligible_cards_in_view": step.get("eligible_cards_in_view"),
                "selector_counts": step.get("selector_counts"),
            })
            # Advance roughly one viewport at a time, then allow DoorDash's
            # virtualized grid to mount the next cards.  This is intentionally
            # slower than a bare page-down loop but capped well below the
            # longer pauses used between itemPage option-data requests.
            time.sleep(random.uniform(0.6, 1.5))
            if total == last_total:
                stable += 1
                if stable >= 4 and at_bottom:
                    stop_reason = "bottom_stable"
                    break
            else:
                stable = 0
            last_total = total
        client.evaluate(tab_id, COLLECT_STEP_JS)
        collected = client.evaluate(tab_id, COLLECTED_JS, timeout=120) or []
        if isinstance(collected, list):
            items = collected
        else:
            stop_reason = "collected_items_unavailable"
        final_page = discovery_page_state(client, tab_id)
        discovery = summarize_discovery(
            items=items,
            initial_page=initial_page,
            final_page=final_page,
            initial_wait=initial_wait,
            stop_reason=stop_reason,
            scrolls_attempted=scrolls_attempted,
            max_scrolls=max_scrolls,
            scroll_trace=scroll_trace,
        )
    except requests.RequestException as exc:
        checkpoint_observed_items(force=True)
        discovery = summarize_discovery(
            items=items,
            initial_page=initial_page,
            final_page=final_page,
            initial_wait=initial_wait,
            stop_reason="browser_lost_during_discovery",
            scrolls_attempted=scrolls_attempted,
            max_scrolls=max_scrolls,
            scroll_trace=scroll_trace,
        )
        discovery["browser_error"] = {
            "kind": "camofox_evaluate_error",
            "message": response_excerpt(exc),
        }

    if collection_url:
        discovery["collection_state"] = {
            "url": collection_url,
            "selector_contract": list(MENU_CARD_SELECTORS),
        }
    return items, discovery


def build_harvest_status(
    *,
    selected_items: list[dict[str, Any]],
    results: list[dict[str, Any]],
    discovery: dict[str, Any],
    selection: dict[str, Any],
    finished: bool,
) -> dict[str, Any]:
    """Summarize exactly why a harvest can, or cannot, claim completeness.

    ``complete`` is intentionally conservative.  It means every selected item
    received an itemPage payload *and* the selection represents an unbounded
    live discovery that reached the bottom-of-menu condition.  It never means
    merely "the loop ended without raising an exception."
    """
    selected_ids = {str(item["item_id"]) for item in selected_items if item.get("item_id")}
    successful_ids = {
        str(item["item_id"])
        for item in results
        if item.get("item_id") and isinstance(item.get("item_page"), dict)
    }
    failed = [
        {
            "item_id": item.get("item_id"),
            "name": item.get("name"),
            "menu_position": item.get("menu_position"),
            "error": item.get("error") or "itemPage was not captured",
            "capture": item.get("item_page_capture"),
        }
        for item in results
        if item.get("item_id") and not isinstance(item.get("item_page"), dict)
    ]
    failed_ids = {str(item["item_id"]) for item in failed}
    pending_ids = sorted(selected_ids - successful_ids - failed_ids)

    reasons: list[str] = []
    if not finished:
        reasons.append("item_page_capture_in_progress")
    if discovery.get("status") != "complete":
        reasons.append(f"discovery_{discovery.get('stop_reason') or 'not_verified'}")
    if selection.get("source") != "live_discovery":
        reasons.append("item_selection_not_live_verified")
    if selection.get("sample_per_section"):
        reasons.append("item_selection_sampled")
    if selection.get("item_limit"):
        reasons.append("item_selection_limited")
    if not selected_ids:
        reasons.append("no_items_selected")
    if failed:
        reasons.append("item_page_failures")
    if pending_ids:
        reasons.append("item_page_captures_pending")

    if not finished:
        state = "in_progress"
    elif reasons:
        state = "incomplete"
    else:
        state = "complete"

    return {
        "schema_version": 2,
        "state": state,
        "reasons": reasons,
        "discovery": discovery,
        "selection": selection,
        "counts": {
            "selected_items": len(selected_ids),
            "successful_item_pages": len(selected_ids & successful_ids),
            "failed_item_pages": len(failed_ids & selected_ids),
            "pending_item_pages": len(pending_ids),
        },
        "failed_items": failed,
        "pending_item_ids": pending_ids,
    }


def write_harvest(
    path: Path,
    store_url: str,
    store_id: str,
    results: list[dict[str, Any]],
    *,
    selected_items: list[dict[str, Any]],
    discovery: dict[str, Any],
    selection: dict[str, Any],
    finished: bool,
) -> dict[str, Any]:
    """Checkpoint. Called periodically during the run, not just at the end - a
    143-item harvest is ~25 minutes and the browser has been observed dying
    mid-run (see recover_tab), which previously discarded every completed
    fetch."""
    ordered = sorted(results, key=lambda r: r.get("menu_position", 0))
    harvest = build_harvest_status(
        selected_items=selected_items,
        results=ordered,
        discovery=discovery,
        selection=selection,
        finished=finished,
    )
    write_json_checkpoint(path, {
        "source_url": store_url,
        "store_id": store_id,
        # Keep the existing top-level field for the offline parser and older
        # artifacts.  It is derived from the evidence-bearing state above,
        # never supplied by a caller as an optimistic assertion.
        "complete": harvest["state"] == "complete",
        "harvest": harvest,
        "items": ordered,
    })
    return harvest


def canonical_store_url(url: str) -> str:
    """Compare DoorDash store targets without volatile query strings/fragments."""
    parsed = urlsplit(url)
    path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def store_id_from_url(url: str) -> str | None:
    """Extract DoorDash's store ID from its normal ``/store/<slug-id>/...`` URL."""
    parts = [part for part in urlsplit(url).path.split("/") if part]
    try:
        store_index = parts.index("store")
    except ValueError:
        return None
    for part in parts[store_index + 1:]:
        suffix = part.rsplit("-", 1)[-1]
        if suffix.isdigit():
            return suffix
    return None


def verify_tab_store(client: CamofoxClient, tab_id: str, store_id: str) -> dict[str, Any]:
    """Require a live tab to identify itself as the intended DoorDash store."""
    try:
        url = client.evaluate(tab_id, "location.href")
    except requests.RequestException as exc:
        return {"status": "unavailable", "message": response_excerpt(exc)}
    if not isinstance(url, str) or not url:
        return {"status": "unverified", "message": "location.href was unavailable"}
    observed_store_id = store_id_from_url(url)
    if observed_store_id is None:
        return {"status": "unverified", "url": canonical_store_url(url), "message": "store ID not present in URL"}
    if observed_store_id != str(store_id):
        return {
            "status": "mismatch",
            "url": canonical_store_url(url),
            "expected_store_id": str(store_id),
            "observed_store_id": observed_store_id,
        }
    return {"status": "match", "url": canonical_store_url(url), "store_id": observed_store_id}


def selection_contract(selection: dict[str, Any]) -> dict[str, Any]:
    """The fields that make a checkpoint's requested item set comparable."""
    return {
        key: selection.get(key)
        for key in ("source", "sample_per_section", "sample_seed", "item_limit")
    }


def merged_section_memberships(*records: dict[str, Any]) -> list[str]:
    memberships: list[str] = []
    for record in records:
        values = record.get("sections")
        if not isinstance(values, list):
            values = [record.get("section")]
        for value in values:
            if isinstance(value, str) and value and value not in memberships:
                memberships.append(value)
    return memberships


def merge_checkpoint_item(checkpoint_item: dict[str, Any], selected_item: dict[str, Any]) -> dict[str, Any]:
    """Retain a validated payload while refreshing current discovery metadata."""
    merged = {**checkpoint_item, **selected_item}
    memberships = merged_section_memberships(selected_item, checkpoint_item)
    if memberships:
        merged["sections"] = memberships
        merged["section"] = memberships[0]
    return merged


def upsert_capture_result(results_by_id: dict[str, dict[str, Any]], result: dict[str, Any]) -> None:
    """Keep one coherent record per DoorDash item across retries and resumes."""
    item_id = result.get("item_id")
    if item_id is None:
        return
    key = str(item_id)
    existing = results_by_id.get(key)
    if existing and isinstance(existing.get("item_page"), dict) and not isinstance(result.get("item_page"), dict):
        # A later transient failure must not overwrite an already validated
        # payload from this same verified selection.
        return
    if existing:
        result = merge_checkpoint_item(existing, result)
    results_by_id[key] = result


def ordered_capture_results(results_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(results_by_id.values(), key=lambda result: result.get("menu_position", 0))


def load_previous(
    path: Path,
    *,
    store_url: str,
    store_id: str,
    selection: dict[str, Any],
    selected_items: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], str | None]:
    """Reuse only checkpoint successes proven compatible with this exact run.

    Pre-contract artifacts are deliberately not resumed: their store, discovery,
    and selection evidence is insufficient to prove they belong to this run.
    They remain fully usable by the offline parser.
    """
    if not path.exists():
        return {}, None
    try:
        doc = json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}, "checkpoint_not_json"
    harvest = doc.get("harvest")
    if not isinstance(harvest, dict) or harvest.get("schema_version") != 2:
        return {}, "checkpoint_has_no_compatible_harvest_contract"
    if str(doc.get("store_id")) != str(store_id):
        return {}, "checkpoint_store_id_mismatch"
    if canonical_store_url(str(doc.get("source_url") or "")) != canonical_store_url(store_url):
        return {}, "checkpoint_store_url_mismatch"
    if selection_contract(harvest.get("selection") or {}) != selection_contract(selection):
        return {}, "checkpoint_selection_mismatch"

    selected_by_id = {str(item["item_id"]): item for item in selected_items if item.get("item_id")}
    previous: dict[str, dict[str, Any]] = {}
    for item in doc.get("items") or []:
        item_id = item.get("item_id")
        if item_id is None or not isinstance(item.get("item_page"), dict):
            continue
        selected_item = selected_by_id.get(str(item_id))
        if selected_item is None:
            continue
        previous[str(item_id)] = merge_checkpoint_item(item, selected_item)
    return previous, None


def discovery_checkpoint_path(harvest_path: Path) -> Path:
    return harvest_path.with_name(f"{harvest_path.stem}.discovery.json")


def write_discovery_checkpoint(
    path: Path,
    *,
    store_url: str,
    store_id: str,
    items: list[dict[str, Any]],
    discovery: dict[str, Any] | None,
    state: str,
) -> None:
    write_json_checkpoint(path, {
        "schema_version": 1,
        "state": state,
        "source_url": store_url,
        "store_id": str(store_id),
        "discovery": discovery,
        "items": items,
    })


def load_completed_discovery_checkpoint(
    path: Path,
    *,
    store_url: str,
    store_id: str,
) -> tuple[list[dict[str, Any]] | None, dict[str, Any] | None, str | None]:
    """Return only a fully completed discovery sidecar for this exact store."""
    if not path.exists():
        return None, None, None
    try:
        doc = json.loads(path.read_text())
    except json.JSONDecodeError:
        return None, None, "discovery_checkpoint_not_json"
    discovery = doc.get("discovery")
    if doc.get("schema_version") != 1 or doc.get("state") != "complete" or not isinstance(discovery, dict):
        return None, None, "discovery_checkpoint_not_complete"
    if str(doc.get("store_id")) != str(store_id):
        return None, None, "discovery_checkpoint_store_id_mismatch"
    if canonical_store_url(str(doc.get("source_url") or "")) != canonical_store_url(store_url):
        return None, None, "discovery_checkpoint_store_url_mismatch"
    items = doc.get("items")
    if discovery.get("status") != "complete" or not isinstance(items, list) or not items:
        return None, None, "discovery_checkpoint_not_usable"
    return items, discovery, None


def recover_tab(
    client: CamofoxClient,
    store_url: str,
    store_id: str,
    lat: float,
    lon: float,
    tz: str,
) -> str | None:
    """Re-open the store page after the tab (or the whole browser) goes away.

    Confirmed failure mode: mid-harvest the camofox browser exited entirely -
    `browserConnected: false`, zero camoufox processes, and every subsequent
    /evaluate returned 404. Reopening under the same profile restores cookies
    and the session, so the harvest can carry on.
    """
    existing = client.current_tab()
    if existing:
        identity = verify_tab_store(client, existing, store_id)
        if identity.get("status") == "match":
            return existing
        print(f"  refusing existing tab during recovery: {identity}", file=sys.stderr)
        return None
    print("  tab gone - reopening store page", file=sys.stderr)
    try:
        tab_id = client.open_tab(store_url, lat, lon, tz)
    except requests.RequestException as exc:
        print(f"  reopen failed: {exc}", file=sys.stderr)
        return None
    client.wait(tab_id, timeout_ms=25000)
    time.sleep(3)
    dismiss_interstitials(client, tab_id)
    identity = verify_tab_store(client, tab_id, store_id)
    if identity.get("status") != "match":
        print(f"  recovered tab did not match target store: {identity}", file=sys.stderr)
        return None
    return tab_id


def response_excerpt(value: Any, limit: int = 600) -> str:
    """Keep failure artifacts useful without embedding arbitrary response bodies."""
    text = " ".join(str(value or "").split())
    return text[:limit]


def item_page_failure(kind: str, *, retryable: bool = False, **details: Any) -> dict[str, Any]:
    return {
        "ok": False,
        "item_page": None,
        "diagnostic": {
            "outcome": "failure",
            "kind": kind,
            "retryable": retryable,
            **details,
        },
    }


def should_retry_item_page_capture(diagnostic: dict[str, Any], attempt: int) -> bool:
    """Whether this completed attempt is eligible for one more itemPage request."""
    return attempt < MAX_ITEM_PAGE_CAPTURE_ATTEMPTS and bool(diagnostic.get("retryable"))


def fetch_item_page(
    client: CamofoxClient,
    tab_id: str,
    store_id: str,
    item_id: str,
    query: str,
) -> dict[str, Any]:
    """Fetch and validate one ``itemPage`` response with a durable diagnosis.

    A successful HTTP response is not sufficient: GraphQL can return errors
    with HTTP 200, and a changed/incorrect payload can otherwise look like an
    empty modifier list.  The returned diagnostic is compact enough to persist
    beside the affected item in a checkpoint.
    """
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
        # This is a Camofox/browser-control failure, not an HTTP response from
        # DoorDash.  The caller may reopen the tab and retry once.
        return item_page_failure(
            "camofox_evaluate_error",
            retryable=True,
            message=response_excerpt(exc),
            requested_item_id=str(item_id),
        )
    if not isinstance(result, dict):
        return item_page_failure(
            "camofox_evaluate_invalid_result",
            retryable=True,
            result_type=type(result).__name__,
            requested_item_id=str(item_id),
        )
    if result.get("fetch_error"):
        return item_page_failure(
            "network_fetch_error",
            retryable=True,
            message=response_excerpt(result.get("fetch_error")),
            requested_item_id=str(item_id),
        )

    status = result.get("status")
    if not isinstance(status, int):
        return item_page_failure(
            "malformed_response_wrapper",
            status_value=repr(status),
            requested_item_id=str(item_id),
        )
    body = result.get("body")
    if not isinstance(body, str):
        return item_page_failure(
            "malformed_response_wrapper",
            http_status=status,
            body_type=type(body).__name__,
            requested_item_id=str(item_id),
        )
    response_meta = {
        "http_status": status,
        "http_status_text": response_excerpt(result.get("status_text"), 160),
        "content_type": response_excerpt(result.get("content_type"), 160),
        "response_bytes": len(body.encode("utf-8")),
        "requested_item_id": str(item_id),
    }
    if not 200 <= status < 300:
        return item_page_failure(
            "http_error",
            retryable=status == 408 or status == 429 or status >= 500,
            response_excerpt=response_excerpt(body),
            **response_meta,
        )
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        return item_page_failure(
            "response_not_json",
            response_excerpt=response_excerpt(body),
            json_error=response_excerpt(exc),
            **response_meta,
        )
    if not isinstance(parsed, dict):
        return item_page_failure("malformed_graphql_payload", payload_type=type(parsed).__name__, **response_meta)

    graphql_errors = parsed.get("errors")
    if graphql_errors:
        errors = graphql_errors if isinstance(graphql_errors, list) else [graphql_errors]
        error_summaries = []
        for error in errors[:3]:
            if isinstance(error, dict):
                summary = {key: error.get(key) for key in ("message", "path") if error.get(key) is not None}
                extensions = error.get("extensions")
                if isinstance(extensions, dict) and extensions.get("code") is not None:
                    summary["code"] = extensions["code"]
                error_summaries.append(summary or {"value": response_excerpt(error)})
            else:
                error_summaries.append({"value": response_excerpt(error)})
        return item_page_failure("graphql_errors", graphql_errors=error_summaries, **response_meta)

    data = parsed.get("data")
    if not isinstance(data, dict):
        return item_page_failure("malformed_graphql_payload", missing="data", **response_meta)
    page = data.get("itemPage")
    if not isinstance(page, dict):
        return item_page_failure("missing_item_page", item_page_type=type(page).__name__, **response_meta)
    header = page.get("itemHeader")
    if not isinstance(header, dict):
        return item_page_failure("malformed_item_page", missing="itemHeader", **response_meta)
    response_item_id = header.get("id")
    if response_item_id is None:
        return item_page_failure("malformed_item_page", missing="itemHeader.id", **response_meta)
    if str(response_item_id) != str(item_id):
        return item_page_failure(
            "item_identity_mismatch",
            response_item_id=str(response_item_id),
            **response_meta,
        )
    return {
        "ok": True,
        "item_page": page,
        "diagnostic": {
            "outcome": "success",
            "response_item_id": str(response_item_id),
            **response_meta,
        },
    }


def sample_items_by_section(
    items: list[dict[str, Any]],
    sample_per_section: int,
    sample_seed: int | None,
) -> tuple[list[dict[str, Any]], int]:
    """Sample every observed category, returning each selected item only once.

    A recommendation shelf is still a real category membership for diagnostic
    sampling.  Its selected cards may overlap the restaurant's ordinary menu
    sections, so the final list restores menu order and de-duplicates by item
    ID before itemPage requests are issued.
    """
    rng = random.Random(sample_seed)
    by_section: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        for section in item_section_memberships(item):
            by_section.setdefault(section, []).append(item)

    selected_ids: set[str] = set()
    for section in sorted(by_section):
        choices = by_section[section]
        for item in rng.sample(choices, min(sample_per_section, len(choices))):
            item_id = item.get("item_id")
            if item_id is not None:
                selected_ids.add(str(item_id))
    return [item for item in items if str(item.get("item_id")) in selected_ids], len(by_section)


def cmd_items(client: CamofoxClient, args: argparse.Namespace) -> None:
    tab_id = require_tab(client)
    items, discovery = collect_items(client, tab_id, checkpoint_path=args.output)
    sections: dict[str, int] = {}
    for it in items:
        for section in item_section_memberships(it):
            sections[section] = sections.get(section, 0) + 1
    print(f"{len(items)} items across {len(sections)} sections")
    for name, count in sections.items():
        print(f"  {count:>3}  {name}")
    print(f"Discovery: {discovery['status']} ({discovery['stop_reason']})")
    if args.output:
        write_json_checkpoint(args.output, items)
        print(f"Wrote {args.output}")


def cmd_harvest(client: CamofoxClient, args: argparse.Namespace) -> None:
    tab_id = require_tab(client)
    if not QUERY_PATH.exists():
        print(f"Missing GraphQL query at {QUERY_PATH} (captured from a traced item click).", file=sys.stderr)
        sys.exit(2)
    query = QUERY_PATH.read_text()

    store_id = str(args.store_id)
    tab_identity = verify_tab_store(client, tab_id, store_id)
    if tab_identity.get("status") != "match":
        print(f"Open tab is not verified for store {store_id}: {tab_identity}", file=sys.stderr)
        sys.exit(2)
    store_url = tab_identity["url"]
    if args.url:
        requested_url = canonical_store_url(args.url)
        if store_id_from_url(requested_url) != store_id or requested_url != store_url:
            print(
                f"--url does not identify the same store request as the live tab: "
                f"{requested_url!r} vs {store_url!r}",
                file=sys.stderr,
            )
            sys.exit(2)

    discovery_path = discovery_checkpoint_path(args.output)
    if args.items_file:
        try:
            loaded_items = json.loads(args.items_file.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Could not read --items-file {args.items_file}: {exc}", file=sys.stderr)
            sys.exit(2)
        if not isinstance(loaded_items, list):
            print(f"--items-file {args.items_file} must contain a JSON item array.", file=sys.stderr)
            sys.exit(2)
        items = loaded_items
        discovery = {
            "source": "items_file",
            "status": "unverified",
            "stop_reason": "items_file_supplied",
            "observed_item_count": len(items),
        }
    else:
        cached_items = cached_discovery = None
        cached_reason = None
        if args.resume:
            cached_items, cached_discovery, cached_reason = load_completed_discovery_checkpoint(
                discovery_path, store_url=store_url, store_id=store_id,
            )
        if cached_items is not None and cached_discovery is not None:
            items, discovery = cached_items, cached_discovery
            print(f"Reusing completed discovery: {len(items)} items from {discovery_path}")
        else:
            if cached_reason:
                print(f"Ignoring discovery checkpoint: {cached_reason}", file=sys.stderr)

            def checkpoint_discovery(observed_items: list[dict[str, Any]]) -> None:
                write_discovery_checkpoint(
                    discovery_path,
                    store_url=store_url,
                    store_id=store_id,
                    items=observed_items,
                    discovery=None,
                    state="in_progress",
                )

            items, discovery = collect_items(client, tab_id, checkpoint_callback=checkpoint_discovery)
            write_discovery_checkpoint(
                discovery_path,
                store_url=store_url,
                store_id=store_id,
                items=items,
                discovery=discovery,
                state=discovery["status"],
            )

    if args.sample_per_section:
        items, section_count = sample_items_by_section(items, args.sample_per_section, args.sample_seed)
        print(
            f"Stratified sample: {len(items)} unique items from {section_count} sections "
            f"({args.sample_per_section} per section, seed={args.sample_seed})"
        )
    if args.limit:
        items = items[: args.limit]

    selection = {
        "source": "items_file" if args.items_file else "live_discovery",
        "sample_per_section": args.sample_per_section or None,
        "sample_seed": args.sample_seed if args.sample_per_section else None,
        "item_limit": args.limit or None,
        "selected_item_count": len(items),
    }

    # Menu order is recorded so output stays stable, but the *fetch* order is
    # shuffled: walking a menu strictly top-to-bottom is a machine tell, and it
    # also makes each session's request sequence identical for a given store.
    for position, item in enumerate(items):
        item["menu_position"] = position
    fetch_order = list(items)
    if args.pacing != "fast":
        random.shuffle(fetch_order)

    pacer = Pacer(args.pacing)
    previous: dict[str, dict[str, Any]] = {}
    resume_reason = None
    if args.resume:
        previous, resume_reason = load_previous(
            args.output,
            store_url=store_url,
            store_id=store_id,
            selection=selection,
            selected_items=items,
        )
    if resume_reason:
        print(f"Ignoring harvest checkpoint: {resume_reason}", file=sys.stderr)
    if previous:
        print(f"Resuming: {len(previous)} items already captured in {args.output}")
        fetch_order = [i for i in fetch_order if str(i["item_id"]) not in previous]
    print(f"Harvesting optionLists for {len(fetch_order)} items (store {store_id}, pacing={args.pacing})")

    results_by_id = dict(previous)
    failures = 0
    fetch_total = len(fetch_order)
    for i, item in enumerate(fetch_order, 1):
        slept = pacer.wait()
        page = None
        capture: dict[str, Any] | None = None
        capture_attempts: list[dict[str, Any]] = []
        for attempt in range(1, MAX_ITEM_PAGE_CAPTURE_ATTEMPTS + 1):
            capture = fetch_item_page(client, tab_id, store_id, item["item_id"], query)
            diagnostic = capture["diagnostic"]
            diagnostic["attempt"] = attempt
            diagnostic["max_attempts"] = MAX_ITEM_PAGE_CAPTURE_ATTEMPTS
            capture_attempts.append(diagnostic)
            if capture["ok"]:
                page = capture["item_page"]
                break

            if should_retry_item_page_capture(diagnostic, attempt):
                write_harvest(
                    args.output, store_url, store_id, ordered_capture_results(results_by_id),
                    selected_items=items, discovery=discovery, selection=selection, finished=False,
                )
                if diagnostic["kind"] in {"camofox_evaluate_error", "camofox_evaluate_invalid_result"}:
                    print(
                        f"  [{i}/{fetch_total}] browser/Camofox failure "
                        f"({diagnostic['kind']}); attempt {attempt}",
                        file=sys.stderr,
                    )
                    recovered = recover_tab(
                        client, store_url, store_id, args.latitude, args.longitude, args.timezone,
                    )
                    if not recovered:
                        print("  could not recover browser - stopping early; rerun to resume", file=sys.stderr)
                        failures += 1
                        upsert_capture_result(results_by_id, {
                            **item,
                            "item_page": None,
                            "error": diagnostic["kind"],
                            "item_page_capture": diagnostic,
                            "item_page_capture_attempts": capture_attempts,
                        })
                        write_harvest(
                            args.output, store_url, store_id, ordered_capture_results(results_by_id),
                            selected_items=items, discovery=discovery, selection=selection, finished=False,
                        )
                        print(f"\nWrote {args.output} ({len(results_by_id)} items captured, INCOMPLETE)")
                        return
                    tab_id = recovered
                else:
                    retry_pause = random.uniform(1.0, 2.0)
                    print(
                        f"  [{i}/{fetch_total}] retryable {diagnostic['kind']} "
                        f"({retry_pause:.1f}s backoff; attempt {attempt})",
                        file=sys.stderr,
                    )
                    time.sleep(retry_pause)
                continue
            break
        if page is None:
            failures += 1
            diagnostic = (capture or {}).get("diagnostic") or {
                "outcome": "failure", "kind": "item_page_capture_unknown", "retryable": False,
            }
            print(
                f"  [{i}/{fetch_total}] FAILED {item['name']!r} ({item['item_id']}; "
                f"{diagnostic['kind']})"
            )
            upsert_capture_result(results_by_id, {
                **item,
                "item_page": None,
                "error": diagnostic["kind"],
                "item_page_capture": diagnostic,
                "item_page_capture_attempts": capture_attempts,
            })
            write_harvest(
                args.output, store_url, store_id, ordered_capture_results(results_by_id),
                selected_items=items, discovery=discovery, selection=selection, finished=False,
            )
            continue
        groups = page.get("optionLists") or []
        required = sum(1 for g in groups if not g.get("isOptional"))
        nested = sum(1 for g in groups for o in g.get("options") or [] if o.get("nestedExtrasList"))
        nested_note = f" +{nested} nested" if nested else ""
        print(f"  [{i}/{fetch_total}] {slept:>5.1f}s  {item['name'][:38]:<38} "
              f"{len(groups)} groups ({required} req){nested_note}")
        result_entry = {**item, "item_page": page, "item_page_capture": capture["diagnostic"]}
        if len(capture_attempts) > 1:
            result_entry["item_page_capture_attempts"] = capture_attempts
        upsert_capture_result(results_by_id, result_entry)
        # Persist every item response immediately. This lets an interrupted
        # harvest resume with no more than its in-flight request lost.
        write_harvest(
            args.output, store_url, store_id, ordered_capture_results(results_by_id),
            selected_items=items, discovery=discovery, selection=selection, finished=False,
        )

    results = ordered_capture_results(results_by_id)
    print(f"  elapsed in deliberate pauses: {pacer.total_slept/60:.1f} min")

    harvest = write_harvest(
        args.output, store_url, store_id, results,
        selected_items=items, discovery=discovery, selection=selection, finished=True,
    )
    print(
        f"\nWrote {args.output} ({len(results)} items, {failures} failures; "
        f"{harvest['state']}: {', '.join(harvest['reasons']) or 'all checks passed'})"
    )


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
    p_harvest.add_argument("--items-file", type=Path,
                           help="reuse a prior `items` JSON array for development; a bare array is unverified and always yields an incomplete harvest")
    p_harvest.add_argument("--sample-per-section", type=int, default=0,
                           help="randomly select this many items from each menu section (0 = all)")
    p_harvest.add_argument("--sample-seed", type=int, default=20260813,
                           help="deterministic random seed used with --sample-per-section")
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
