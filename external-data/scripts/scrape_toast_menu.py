#!/usr/bin/env python3
"""Scrape a Toast Online Ordering menu via a running camofox-browser server.

Companion to parse_toast_menu.py, which already folds the "Featured Items"
rollup into its real category by durable item id - this script only
produces that parser's expected raw input: {"result": [{item_id, section,
name, description, price}, ...]}.

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


def scrape(args: argparse.Namespace) -> None:
    client = CamofoxClient(args.server, args.user)
    if not client.health():
        print(f"camofox-browser server not reachable at {args.server}. Start it first (camofox-startup skill).", file=sys.stderr)
        sys.exit(2)

    tab_id = client.open_tab(args.url, args.latitude, args.longitude, args.timezone)
    try:
        client.wait(tab_id, timeout_ms=15000)
        time.sleep(2)  # let the SPA finish its initial render pass

        entries = client.evaluate(tab_id, EXTRACT_MENU_JS) or []
        final_url = client.evaluate(tab_id, "location.href")
    finally:
        client.close_tab(tab_id)
        client.close_session()

    output = {"source_url": args.url, "final_url": final_url, "result": entries}
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    section_count = len({e["section"] for e in entries if e.get("section")})
    print(f"Wrote {args.output} ({section_count} sections, {len(entries)} items)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url", help="Toast order page, e.g. https://<restaurant>/order?diningOption=takeout")
    parser.add_argument("output", type=Path)
    parser.add_argument("--latitude", type=float, default=42.197513)
    parser.add_argument("--longitude", type=float, default=-83.269677)
    parser.add_argument("--timezone", default="America/Detroit")
    parser.add_argument("--server", default="http://localhost:9377")
    parser.add_argument("--user", default="toast-scraper", help="camofox-browser profile id")
    args = parser.parse_args()
    scrape(args)


if __name__ == "__main__":
    main()
