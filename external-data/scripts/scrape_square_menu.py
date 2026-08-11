#!/usr/bin/env python3
"""Scrape a Square Online (square.site) menu via a running camofox-browser server.

Companion to parse_square_menu.py, which already handles the
category/badge assignment - this script only produces that parser's
expected raw input: {"result": [{category, name, description, price,
badge}, ...]}.

Confirmed live against Motz's Burgers (https://motzs-burgers-southgate.square.site/):

- A "Select location" modal covers the page on every load, regardless of
  open/closed status - not a "closed" notice, just a mandatory step this
  Weebly/EditMySite-powered storefront always shows. It has a "View menu"
  button (inside `[role="dialog"]`, the last `<button>` in it on the
  sampled restaurant) that dismisses it and reveals the same menu
  underneath - no need to actually pick a location to get there.
- No JSON-LD or embedded state - everything comes from a DOM pass over
  `.grid__item` cards:
    - Name: `.w-product-title`.
    - Description: `.w-product-description`.
    - Price: `.product-price__wrapper`.
    - Badge: Square supports a generic `.badge-around` badge template a
      restaurant can label anything (e.g. "Popular", "New"), but it was
      present in the markup and unset on every item on the sampled
      restaurant, so the `[class*="badge"]:not(.badge-around)` selector
      used here to read the label text is a best-effort guess at the
      populated case, not confirmed against a real example.
- Category headers are `.category-title__container` elements, matched to
  each item card by nearest-preceding position in DOM order (same pattern
  used for Toast/AppFront/Clover). Their text has stray leading whitespace
  and an "Available X - Y" line glued on after the actual category name,
  so only the first trimmed line is kept.
- The menu lazy-loads on scroll like DoorDash/Grubhub (13 of 16 items were
  mounted before any scrolling on the sampled restaurant), so this polls
  the mounted item count for stability rather than reading once.

Every click is preceded by a randomized human-paced delay - see
CAMOFOX-startup skill guidance on not issuing instant, back-to-back
actions.

Requires the camofox-browser server already running (see the
camofox-startup skill / `camofox server start`).
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
  const headers = Array.from(document.querySelectorAll('.category-title__container'));
  const cards = Array.from(document.querySelectorAll('.grid__item'));
  const all = [
    ...headers.map(function(h) { return { type: 'header', el: h, text: h.textContent.trim().split('\n')[0].trim() }; }),
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
    const nameEl = card.querySelector('.w-product-title');
    const descEl = card.querySelector('.w-product-description');
    const priceEl = card.querySelector('.product-price__wrapper');
    const badgeWrap = card.querySelector('.badge-around');
    const badgeEl = badgeWrap ? badgeWrap.querySelector('[class*="badge"]:not(.badge-around)') : null;
    results.push({
      category: current,
      name: nameEl ? nameEl.textContent.trim() : null,
      description: descEl ? descEl.textContent.trim() : '',
      price: priceEl ? priceEl.textContent.trim() : null,
      badge: badgeEl && badgeEl.textContent.trim() ? badgeEl.textContent.trim() : null,
    });
  }
  return JSON.stringify(results);
})()
""".strip()

ITEM_COUNT_JS = "document.querySelectorAll('.grid__item').length"


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

    def wait_for_selector(self, tab_id: str, selector: str, timeout_ms: int = 5000, poll_ms: int = 250) -> bool:
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


def human_delay(min_s: float = 0.9, max_s: float = 2.2) -> None:
    """Pause like someone reading the page before their next click."""
    time.sleep(random.uniform(min_s, max_s))


def close_known_modals(client: CamofoxClient, tab_id: str) -> bool:
    """Dismiss the "Select location" modal Square always shows on load via
    its "View menu" button - not closed-store specific, this appears
    regardless of whether the restaurant is currently open."""
    if not client.wait_for_selector(tab_id, '[role="dialog"]', timeout_ms=5000):
        return False
    human_delay(0.5, 1.4)
    return client.click(tab_id, '[role="dialog"] >> text="View menu"')


def scroll_until_stable(client: CamofoxClient, tab_id: str, max_passes: int = 15) -> int:
    """Scroll to the bottom repeatedly until the mounted item count stops
    growing across two consecutive passes (or max_passes is hit) - this
    menu lazy-loads like DoorDash/Grubhub's virtualized lists."""
    last_count = -1
    for _ in range(max_passes):
        count = client.evaluate(tab_id, ITEM_COUNT_JS) or 0
        if count == last_count:
            return count
        last_count = count
        client.evaluate(tab_id, "window.scrollBy(0, 2400); null")
        human_delay(0.5, 1.2)
    return last_count


def scrape(args: argparse.Namespace) -> None:
    client = CamofoxClient(args.server, args.user)
    if not client.health():
        print(f"camofox-browser server not reachable at {args.server}. Start it first (camofox-startup skill).", file=sys.stderr)
        sys.exit(2)

    tab_id = client.open_tab(args.url, args.latitude, args.longitude, args.timezone)
    try:
        client.wait(tab_id, timeout_ms=15000)
        human_delay(1.5, 2.5)
        close_known_modals(client, tab_id)

        item_count = scroll_until_stable(client, tab_id)
        entries = client.evaluate(tab_id, EXTRACT_MENU_JS) or []
        final_url = client.evaluate(tab_id, "location.href")
    finally:
        client.close_tab(tab_id)
        client.close_session()

    output = {"source_url": args.url, "final_url": final_url, "result": entries}
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    section_count = len({e["category"] for e in entries if e.get("category")})
    print(f"Wrote {args.output} ({section_count} sections, {item_count} items)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url", help="Square Online storefront, e.g. https://<slug>.square.site/")
    parser.add_argument("output", type=Path)
    parser.add_argument("--latitude", type=float, default=42.197513)
    parser.add_argument("--longitude", type=float, default=-83.269677)
    parser.add_argument("--timezone", default="America/Detroit")
    parser.add_argument("--server", default="http://localhost:9377")
    parser.add_argument("--user", default="square-scraper", help="camofox-browser profile id")
    args = parser.parse_args()
    scrape(args)


if __name__ == "__main__":
    main()
