#!/usr/bin/env python3
"""Scrape a Toast Online Ordering menu via a running camofox-browser server.

Companion to parse_toast_menu.py, which folds the "Featured Items" rollup
into its real category by durable item id. In addition to the card inventory,
this script opens every distinct item and captures its configuration modal:
{"result": [{item_id, section, name, description, price, option_groups}, ...]}.

Confirmed live against The Taco Company
(https://tacocompanyusa.com/order?diningOption=takeout, same DOM whether
loaded from the restaurant's own domain or the toasttab.com mirror):

- No JSON-LD/embedded state - Toast renders everything client-side, so this
  is a DOM scrape like Clover/Square/Cash App, not a JSON-LD read like Uber
  Eats/DoorDash.
- Every item card is an `a[data-testid="add-to-cart-<uuid>"]`. That same
  uuid is reused on the duplicate card inside "Featured Items", which is
  how parse_toast_menu.py folds the rollup without name-matching.
  - Name: `.headerText` (inside an `h3`).
  - Description: `[data-testid="item-content-description"]`.
  - Price: `.price`.
- Category headers are also plain `h3` elements with no distinguishing
  class - identical tag to an item's own name `h3`. The only way to tell
  them apart is that an item name's `h3` is nested inside its
  `a[data-testid^="add-to-cart-"]` card and a real category header's is
  not, so headers are collected by filtering that out, then interleaved
  with item cards in DOM order (same pattern used for AppFront/Clover).
- The whole menu (70 items on the sampled restaurant) was already mounted
  with no scrolling needed - Toast doesn't virtualize like
  DoorDash/Grubhub/Square do.
- A closed/"scheduled orders only" restaurant shows a non-blocking inline
  banner ("Only accepting scheduled orders"), not a modal - confirmed live
  while this restaurant was actually outside its hours, so there's nothing
  to dismiss before scraping.
- Clicking an item opens a `[role="dialog"]` configuration modal. Each
  `[data-testid="selection-list"]` is one modifier group; its `.modSectionTitle`
  and `.modSectionSubtitle` supply the group title and Required/Optional state,
  while the native checkbox/radio inputs and their labels supply choices and
  prices. Confirmed against Tru Pizza Co.'s Build Your Own Regular Handtossed.

Requires the camofox-browser server already running (see the camofox-startup
skill / `camofox server start`).
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

EXTRACT_MENU_JS = r"""
(function() {
  const headers = Array.from(document.querySelectorAll('h3'))
    .filter(function(h) { return !h.closest('a[data-testid^="add-to-cart-"]'); });
  const cards = Array.from(document.querySelectorAll('a[data-testid^="add-to-cart-"]'));
  const all = [
    ...headers.map(function(h) { return { type: 'header', el: h, text: h.textContent.trim() }; }),
    ...cards.map(function(c) { return { type: 'item', el: c }; }),
  ];
  all.sort(function(a, b) { return (a.el.compareDocumentPosition(b.el) & Node.DOCUMENT_POSITION_FOLLOWING) ? -1 : 1; });
  let current = null;
  const results = [];
  for (const entry of all) {
    if (entry.type === 'header') {
      current = entry.text;
      continue;
    }
    const card = entry.el;
    const itemId = card.getAttribute('data-testid').replace('add-to-cart-', '');
    const nameEl = card.querySelector('.headerText');
    const descEl = card.querySelector('[data-testid="item-content-description"]');
    const priceEl = card.querySelector('.price');
    results.push({
      item_id: itemId,
      section: current,
      name: nameEl ? nameEl.textContent.trim() : null,
      description: descEl ? descEl.textContent.trim() : '',
      price: priceEl ? priceEl.textContent.trim() : null,
    });
  }
  return JSON.stringify(results);
})()
""".strip()


OPEN_ITEM_JS = r"""
(function(itemId) {
  const target = 'add-to-cart-' + itemId;
  const card = Array.from(document.querySelectorAll('a[data-testid^="add-to-cart-"]'))
    .find(function(el) { return el.getAttribute('data-testid') === target; });
  if (!card) return false;
  card.click();
  return true;
})(%s)
""".strip()


EXTRACT_MODAL_JS = r"""
(function() {
  const dialog = document.querySelector('[role="dialog"]');
  if (!dialog) return null;
  const clean = function(value) { return String(value || '').replace(/\s+/g, ' ').trim(); };
  const money = function(value) {
    const match = clean(value).match(/(?:\+\s*)?\$(\d+(?:\.\d{2})?)/);
    return match ? Number(match[1]) : 0;
  };
  const groups = Array.from(dialog.querySelectorAll('[data-testid="selection-list"]'))
    .map(function(group) {
      const subtitle = clean(group.querySelector('.modSectionSubtitle')?.textContent);
      const controls = Array.from(group.querySelectorAll('input[type="checkbox"], input[type="radio"]'));
      const options = controls.map(function(input) {
        const label = input.id ? group.querySelector('label[for="' + CSS.escape(input.id) + '"]') : null;
        const text = clean(label?.textContent || input.name || '');
        const price = money(text);
        const name = clean(text.replace(/(?:\+\s*)?\$\d+(?:\.\d{2})?/g, '')) || clean(input.name).replace(/^[^-]+-/, '');
        return { name: name, price: price, control: input.type };
      });
      return {
        group: clean(group.querySelector('.modSectionTitle h3')?.textContent),
        subtitle: subtitle,
        required: /required/i.test(subtitle) && !/optional/i.test(subtitle),
        selection: controls.some(function(input) { return input.type === 'radio'; }) ? 'single_select' : 'multi_select',
        options: options,
      };
    })
    .filter(function(group) { return group.group || group.options.length; });
  return {
    title: clean(dialog.querySelector('[data-testid="modal-content"] h1, [data-testid="modal-content"] h2, .itemModal h1, .itemModal h2')?.textContent),
    option_groups: groups,
  };
})()
""".strip()


# Toast mounts the dialog shell before it mounts modifier rows.  Waiting only
# for ``[role=dialog]`` therefore races the real form and can record a false
# empty option list.  A modal without modifiers reaches the bounded timeout and
# is still recorded as an empty configuration; a modal with choices is held
# until its native control rows are present.
MODAL_OPTION_INPUTS_READY_JS = r"""
Boolean(document.querySelector(
  '[role="dialog"] [data-testid="selection-list"] input[type="checkbox"], '
  + '[role="dialog"] [data-testid="selection-list"] input[type="radio"]'
))
""".strip()


CLOSE_MODAL_JS = r"""
(function() {
  const button = document.querySelector('[role="dialog"] [data-testid="modal-close-button"]');
  if (!button) return false;
  button.click();
  return true;
})()
""".strip()


class Pacer:
    """Human-scale pacing for sequential item modal reads.

    Opening and dismissing visible item modals is quicker than DoorDash's
    background item-page requests: usually 1-3 seconds, with infrequent longer
    pauses when a person actually reads a configuration screen.
    """

    def __init__(self, mode: str = "human", long_breaks: bool = True) -> None:
        self.mode = mode
        self.long_breaks = long_breaks
        self.count = 0
        self.next_break = random.randint(18, 32)
        self.total_slept = 0.0

    def wait(self) -> float:
        if self.mode == "fast":
            delay = random.uniform(0.9, 2.2)
        else:
            self.count += 1
            if self.long_breaks and self.count >= self.next_break:
                # A real step-away, deliberately sparse for this visible and
                # comparatively quick modal-browsing workflow.
                delay = random.uniform(20, 55)
                self.next_break = self.count + random.randint(18, 32)
            else:
                roll = random.random()
                if roll < 0.025:
                    # Read a dense configuration screen, or briefly switch
                    # attention to something else.
                    delay = min(random.lognormvariate(2.45, 0.35), 22.0)
                elif roll < 0.12:
                    delay = min(random.lognormvariate(1.55, 0.35), 10.0)
                else:
                    # Skew toward a quick scan while staying in the requested
                    # 1-3 second normal-interaction envelope.
                    delay = 1.0 + 2.0 * random.betavariate(2.2, 3.4)
        time.sleep(delay)
        self.total_slept += delay
        return delay


class CamofoxClient:
    def __init__(self, server: str, user_id: str) -> None:
        self.server = server.rstrip("/")
        self.user_id = user_id

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        resp = requests.post(f"{self.server}{path}", json={"userId": self.user_id, **body}, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def health(self) -> bool:
        try:
            return requests.get(f"{self.server}/health", timeout=5).ok
        except requests.RequestException:
            return False

    def open_tab(self, url: str, lat: float, lon: float, timezone_id: str) -> str:
        # camofox's own page.goto deadline is 30s; a 30s HTTP read timeout here
        # expires at the same instant and turns a recoverable slow load into a
        # client-side timeout with no server response to inspect. Give the
        # request room to return camofox's actual error.
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
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["tabId"]

    def wait(self, tab_id: str, timeout_ms: int = 15000) -> None:
        self._post(f"/tabs/{tab_id}/wait", {"timeout": timeout_ms})

    def evaluate(self, tab_id: str, expression: str) -> Any:
        data = self._post(f"/tabs/{tab_id}/evaluate", {"expression": expression})
        result = data.get("result")
        if isinstance(result, str):
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                return result
        return result

    def wait_for_expression(self, tab_id: str, expression: str, timeout_seconds: float = 10) -> bool:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if self.evaluate(tab_id, expression):
                return True
            time.sleep(0.15)
        return False

    def screenshot(self, tab_id: str) -> bytes | None:
        resp = requests.get(f"{self.server}/tabs/{tab_id}/screenshot", params={"userId": self.user_id}, timeout=30)
        resp.raise_for_status()
        return resp.content or None

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


def write_checkpoint(
    path: Path,
    source_url: str,
    final_url: str,
    entries: list[dict[str, Any]],
    complete: bool,
    options_captured: bool = True,
) -> None:
    """Persist a valid raw Toast response after every acquisition step.

    ``options_captured`` records whether the per-item configuration modals were
    opened at all.  Without it a ``--no-options`` run is indistinguishable from
    a run where every item genuinely has no modifiers: both leave the entries
    with no ``option_groups`` key.  A consumer must be able to tell "not asked
    for" apart from "asked for and empty".
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(
            {
                "source_url": source_url,
                "final_url": final_url,
                "complete": complete,
                "options_captured": options_captured,
                "result": entries,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def load_previous_options(
    path: Path, source_url: str
) -> tuple[dict[str, dict[str, Any]], str | None]:
    """Reuse option groups already captured for this exact menu.

    The per-item modal loop is the slow part of a full capture - two paced
    pauses per item, so a 145-item menu runs for tens of minutes and an
    interruption leaves a `complete: false` artifact. `write_checkpoint` already
    persists after every modal, so the finished work is on disk; this reads it
    back so a rerun only fetches what is missing.

    Reuse is deliberately narrow: a checkpoint is only accepted when it came
    from the same source URL and actually captured options. Returns the reusable
    entries keyed by item id, plus a reason when the checkpoint was rejected.
    """
    if not path.exists():
        return {}, None
    try:
        doc = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}, "checkpoint_not_readable_json"
    if str(doc.get("source_url") or "") != source_url:
        return {}, "checkpoint_source_url_mismatch"
    if not doc.get("options_captured", True):
        # A --no-options artifact has no modifier data to resume from.
        return {}, "checkpoint_has_no_captured_options"
    previous: dict[str, dict[str, Any]] = {}
    for entry in doc.get("result") or []:
        item_id = entry.get("item_id")
        if not item_id or item_id in previous:
            continue
        # An EMPTY option_groups is deliberately NOT treated as done. Toast
        # mounts the dialog shell before its modifier rows, so a capture that
        # raced the form records `option_groups: []` that is indistinguishable
        # from a genuinely modifier-less item - the
        # avenue-american-bistro-raw.json capture has 142 such false empties
        # while a targeted re-check of the same items found real option groups.
        # Re-fetching an option-less item costs one modal; reusing a false empty
        # silently locks in wrong data, so this errs toward re-fetching.
        #
        # A recorded modal_error is a completed attempt, not missing work;
        # keeping it prevents a resume loop from retrying it forever. Re-run
        # without --resume to retry those.
        if entry.get("option_groups") or entry.get("modal_error"):
            previous[item_id] = {
                key: entry[key]
                for key in ("option_groups", "modal_error")
                if key in entry
            }
    return previous, None


def scrape(args: argparse.Namespace) -> None:
    client = CamofoxClient(args.server, args.user)
    if not client.health():
        print(f"camofox-browser server not reachable at {args.server}. Start it first (camofox-startup skill).", file=sys.stderr)
        sys.exit(2)

    tab_id = None
    for attempt in range(1, 4):
        try:
            tab_id = client.open_tab(args.url, args.latitude, args.longitude, args.timezone)
            break
        except requests.RequestException as exc:
            # camofox returns HTTP 500 wrapping `page.goto: Timeout 30000ms
            # exceeded` when a heavy page misses the domcontentloaded deadline.
            # Observed transient - the same URL succeeds on a later attempt.
            if attempt == 3:
                print(f"Could not open {args.url}: {exc}", file=sys.stderr)
                sys.exit(2)
            print(f"  tab open failed (attempt {attempt}/3); retrying", file=sys.stderr)
            time.sleep(random.uniform(4.0, 7.0))
    try:
        client.wait(tab_id, timeout_ms=15000)
        time.sleep(2)  # let the SPA finish its initial render pass

        capture_options = not args.no_options
        entries = client.evaluate(tab_id, EXTRACT_MENU_JS) or []
        final_url = client.evaluate(tab_id, "location.href") or args.url
        # The complete card inventory is useful even if a later modal fails.
        write_checkpoint(args.output, args.url, final_url, entries, complete=False,
                         options_captured=capture_options)
        # Toast repeats cards in Featured Items. Open each durable item id once;
        # the card-level rows still retain their original sections for the parser.
        modal_by_item_id: dict[str, dict[str, Any]] = {}
        unique_entries: list[dict[str, Any]] = []
        seen_item_ids: set[str] = set()
        for entry in entries:
            item_id = entry.get("item_id")
            if item_id and item_id not in seen_item_ids:
                seen_item_ids.add(item_id)
                unique_entries.append(entry)

        entries_by_item_id: dict[str, list[dict[str, Any]]] = {}
        for entry in entries:
            if entry.get("item_id"):
                entries_by_item_id.setdefault(entry["item_id"], []).append(entry)

        reused = 0
        if capture_options and args.resume:
            previous, reject_reason = load_previous_options(args.output, args.url)
            if reject_reason:
                print(f"Ignoring checkpoint: {reject_reason}", file=sys.stderr)
            for item_id, modal in previous.items():
                for duplicate in entries_by_item_id.get(item_id, []):
                    duplicate.update(modal)
            # Only skip items whose ids are still on the live menu.
            reusable = {i for i in previous if i in entries_by_item_id}
            reused = len(reusable)
            if reused:
                print(f"Resuming: {reused} items already captured in {args.output}")
                modal_by_item_id.update({i: previous[i] for i in reusable})
                unique_entries = [e for e in unique_entries if e.get("item_id") not in reusable]

        def checkpoint_modal(item_id: str, modal: dict[str, Any]) -> None:
            modal_by_item_id[item_id] = modal
            for duplicate in entries_by_item_id.get(item_id, []):
                duplicate.update(modal)
            write_checkpoint(args.output, args.url, final_url, entries, complete=False,
                             options_captured=capture_options)

        pacer = Pacer(args.pacing, long_breaks=not args.no_long_breaks)
        for index, entry in enumerate(unique_entries if capture_options else [], 1):
            item_id = entry.get("item_id")
            opened = client.evaluate(tab_id, OPEN_ITEM_JS % json.dumps(item_id))
            if not opened:
                checkpoint_modal(item_id, {"option_groups": [], "modal_error": "item card not found"})
                continue
            if not client.wait_for_expression(tab_id, "Boolean(document.querySelector('[role=dialog]'))"):
                checkpoint_modal(item_id, {"option_groups": [], "modal_error": "configuration modal did not open"})
                continue
            # The dialog shell appears before Toast hydrates its modifier rows.
            # Do not extract immediately after the shell is visible, or paid
            # and zero-cost choices will be recorded as a false empty list.
            client.wait_for_expression(tab_id, MODAL_OPTION_INPUTS_READY_JS, timeout_seconds=2)
            checkpoint_modal(item_id, client.evaluate(tab_id, EXTRACT_MODAL_JS) or {"option_groups": []})
            # The delay is deliberately *inside* the visible modal, not between
            # cards.  This models someone reading its configuration before
            # dismissing it, and prevents a flash-open/flash-close pattern.
            delay = pacer.wait()
            client.evaluate(tab_id, CLOSE_MODAL_JS)
            client.wait_for_expression(tab_id, "!document.querySelector('[role=dialog]')", timeout_seconds=5)
            # Closing a modal is also an interaction boundary. Pause again on
            # the menu before choosing the next card instead of immediately
            # opening it.
            post_close_delay = pacer.wait()
            print(f"  [{index}/{len(unique_entries)}] {delay:>5.1f}s visible, "
                  f"{post_close_delay:>5.1f}s after close  {entry.get('name') or item_id}")

        final_url = client.evaluate(tab_id, "location.href")
    finally:
        client.close_tab(tab_id)
        client.close_session()

    write_checkpoint(args.output, args.url, final_url, entries, complete=True,
                     options_captured=capture_options)
    section_count = len({e["section"] for e in entries if e.get("section")})
    if capture_options:
        note = f" ({reused} reused)" if reused else ""
        print(f"Wrote {args.output} ({section_count} sections, {len(entries)} cards; "
              f"{len(modal_by_item_id)} distinct item modals{note}; "
              f"{pacer.total_slept / 60:.1f} min in deliberate pauses)")
    else:
        print(f"Wrote {args.output} ({section_count} sections, {len(entries)} cards, "
              f"{len(unique_entries)} distinct items; OPTIONS NOT CAPTURED (--no-options))")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url", help="Toast order page, e.g. https://<restaurant>/order?diningOption=takeout")
    parser.add_argument("output", type=Path)
    parser.add_argument("--latitude", type=float, default=42.197513)
    parser.add_argument("--longitude", type=float, default=-83.269677)
    parser.add_argument("--timezone", default="America/Detroit")
    parser.add_argument("--server", default="http://localhost:9377")
    parser.add_argument("--user", default="toast-scraper", help="camofox-browser profile id")
    parser.add_argument("--pacing", choices=("human", "fast"), default="human",
                        help="Interaction pacing for sequential configuration-modal reads (default: human).")
    parser.add_argument("--resume", action="store_true",
                        help="reuse option groups already present in the output file and only "
                             "open the items still missing. Requires a checkpoint from the same "
                             "URL that captured options; recorded modal errors count as done.")
    parser.add_argument("--no-options", action="store_true",
                        help="skip the per-item configuration modals; capture only card-level "
                             "name/description/price. Much faster (no modal open/close pacing) and "
                             "enough for a menu/price comparison. The artifact records "
                             "options_captured: false so an empty option list cannot be mistaken "
                             "for a captured-and-empty one.")
    parser.add_argument("--no-long-breaks", action="store_true",
                        help="Keep normal and reading pauses but disable the sparse 20-55 second step-away tier.")
    args = parser.parse_args()
    scrape(args)


if __name__ == "__main__":
    main()
