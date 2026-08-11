#!/usr/bin/env python3
"""Scrape a SpotOn Order (order.spoton.com) menu via a running camofox-browser server.

Companion to parse_spoton_menu.py, which already folds the "Picked For You"
rollup into its real category by exact name - this script only produces
that parser's expected raw input: {"result": [{section, name, description,
price, is_sold_out}, ...]}.

Confirmed live against Brickhouse
(https://order.spoton.com/so-the-brickhouse-7742/wyandotte-mi/BL-6692-FF12-F424/pickup):
117 items across 9 real categories plus a 6-item "Picked For You" rollup;
"Brickhouse Burger" appeared identically (same name/description/price) in
both "Picked For You" and its real category "Burgers & Handhelds".

- No JSON-LD/embedded state - Chakra UI renders everything client-side, so
  this is a DOM scrape like Clover/Square/Toast/Cash App.
- Every item card is `[data-testid="menu-item-card"]` with a `role="button"`
  and a full `aria-label` of "<name>, <description>, <price>" - not used for
  parsing since the individual fields are also each their own element:
  - Name: `[data-testid="menu-item-card-name"]` (inside an `h3`).
  - Description: `[data-testid="menu-item-card-description"]`.
  - Price: `[data-testid="menu-item-card-price"]`.
- Items have no durable id anywhere in the card markup, only the full
  aria-label text - same situation as AppFront, so the "Picked For You"
  rollup (wrapped in a `[data-testid="menu-item-ai-suggested-items"]`
  container, confirmed to be an AI-suggested/featured set, same duplicate-
  category pattern as Uber Eats/DoorDash/Grubhub/AppFront) is folded into
  its real category by exact name match in parse_spoton_menu.py instead of
  by id. Known weak point: two differently-configured items sharing a name
  would incorrectly merge - see that script's docstring.
- Category headers (including "Picked For You" itself) are plain `h2`
  elements, matched to each item card by nearest-preceding position in DOM
  order (same interleaving pattern used for Toast/AppFront/Clover/Square).
- The whole menu (117 items on the sampled restaurant) was already mounted
  with no scrolling needed - confirmed the count doesn't change after
  scrolling to the bottom - but this still does one scroll-and-recheck as a
  cheap safety net in case a bigger menu elsewhere lazy-mounts.
- Sold-out signal (unconfirmed live - no sold-out items on the sampled
  restaurant): `aria-disabled="true"` is present directly on the item card
  itself per SpotOn's own markup, so that's checked first, with the usual
  "sold out"/"unavailable"/"86'd" textContent keyword search as a fallback
  per external-data/menu-scraping/sold-out-detection-notes.md.
- A "Cookie notice" modal (Chakra UI, a `chakra-modal__content` with a
  "Dismiss" button) appeared once during exploration (a different SpotOn
  restaurant than the one this script was validated against) but was not
  reliably reproducible on repeat loads of either restaurant - this script
  makes a short best-effort attempt to dismiss it and proceeds regardless
  of whether one was found, same defensive pattern as Square's
  close_known_modals.

Requires the camofox-browser server already running (see the camofox-startup
skill / `camofox server start`).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import requests

EXTRACT_MENU_JS = r"""
(function() {
  const headers = Array.from(document.querySelectorAll('h2'));
  const cards = Array.from(document.querySelectorAll('[data-testid="menu-item-card"]'));
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
    const nameEl = card.querySelector('[data-testid="menu-item-card-name"]');
    const descEl = card.querySelector('[data-testid="menu-item-card-description"]');
    const priceEl = card.querySelector('[data-testid="menu-item-card-price"]');
    const isSoldOut = card.getAttribute('aria-disabled') === 'true' || /sold out|unavailable|86'd/i.test(card.textContent);
    results.push({
      section: current,
      name: nameEl ? nameEl.textContent.trim() : null,
      description: descEl ? descEl.textContent.trim() : '',
      price: priceEl ? priceEl.textContent.trim() : null,
      is_sold_out: isSoldOut,
    });
  }
  return JSON.stringify(results);
})()
""".strip()

ITEM_COUNT_JS = 'document.querySelectorAll(\'[data-testid="menu-item-card"]\').length'


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
            timeout=30,
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

    def click(self, tab_id: str, selector: str) -> bool:
        try:
            self._post(f"/tabs/{tab_id}/click", {"selector": selector})
            return True
        except requests.RequestException:
            return False

    def wait_for_selector(self, tab_id: str, selector: str, timeout_ms: int = 3000, poll_ms: int = 300) -> bool:
        deadline = time.monotonic() + timeout_ms / 1000
        check_js = f"!!document.querySelector({json.dumps(selector)})"
        while time.monotonic() < deadline:
            if self.evaluate(tab_id, check_js):
                return True
            time.sleep(poll_ms / 1000)
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


def close_known_modals(client: CamofoxClient, tab_id: str) -> bool:
    """Best-effort dismissal of the Chakra UI "Cookie notice" modal - not
    reliably reproducible during exploration, so this doesn't block the
    scrape if the modal never shows up."""
    if not client.wait_for_selector(tab_id, ".chakra-modal__content", timeout_ms=3000):
        return False
    time.sleep(0.6)
    return client.click(tab_id, 'text="Dismiss" >> visible=true')


def scroll_once(client: CamofoxClient, tab_id: str) -> int:
    before = client.evaluate(tab_id, ITEM_COUNT_JS) or 0
    client.evaluate(tab_id, "window.scrollTo(0, document.body.scrollHeight); null")
    time.sleep(1.0)
    after = client.evaluate(tab_id, ITEM_COUNT_JS) or 0
    if after > before:
        print(f"  note: item count grew after scroll ({before} -> {after}); menu may lazy-load more than a single scroll captures", file=sys.stderr)
    return after


def scrape(args: argparse.Namespace) -> None:
    client = CamofoxClient(args.server, args.user)
    if not client.health():
        print(f"camofox-browser server not reachable at {args.server}. Start it first (camofox-startup skill).", file=sys.stderr)
        sys.exit(2)

    tab_id = client.open_tab(args.url, args.latitude, args.longitude, args.timezone)
    try:
        client.wait(tab_id, timeout_ms=15000)
        time.sleep(2)  # let the SPA finish its initial render pass
        close_known_modals(client, tab_id)

        item_count = scroll_once(client, tab_id)
        entries = client.evaluate(tab_id, EXTRACT_MENU_JS) or []
        final_url = client.evaluate(tab_id, "location.href")
    finally:
        client.close_tab(tab_id)
        client.close_session()

    output = {"source_url": args.url, "final_url": final_url, "result": entries}
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    section_count = len({e["section"] for e in entries if e.get("section")})
    sold_out_count = sum(1 for e in entries if e.get("is_sold_out"))
    print(f"Wrote {args.output} ({section_count} sections, {item_count} items, {sold_out_count} sold out)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url", help="SpotOn Order restaurant page, e.g. https://order.spoton.com/<slug>/pickup")
    parser.add_argument("output", type=Path)
    parser.add_argument("--latitude", type=float, default=42.197513)
    parser.add_argument("--longitude", type=float, default=-83.269677)
    parser.add_argument("--timezone", default="America/Detroit")
    parser.add_argument("--server", default="http://localhost:9377")
    parser.add_argument("--user", default="spoton-scraper", help="camofox-browser profile id")
    args = parser.parse_args()
    scrape(args)


if __name__ == "__main__":
    main()
