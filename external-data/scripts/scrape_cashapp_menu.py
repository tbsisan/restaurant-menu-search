#!/usr/bin/env python3
"""Scrape a Cash App (cash.app) local-ordering menu via a running camofox-browser server.

Companion to parse_cashapp_menu.py, which already handles the
section/availability shape - this script only produces that parser's
expected raw input: {"result": [{item_id, section, name, description,
price, is_sold_out}, ...]}.

Cash App restaurants render in one of two card layouts (confirmed live
against Amo Sami's Shawarma and Marco Polo Global Restaurant for the tile
layout, and Marco Polo/Lilly's Munchies for the list layout - the same
seller can apparently pick either template):

- "Tile" layout: cards are `[data-testid^="item-tile-container-<item id>"]`,
  with a durable id in the testid itself. The description lives in a
  `<span>` that's a direct child of the card's *last* direct-child div (a
  wrapper sibling of the name/price block), not a direct child of the card -
  grabbing the wrong scope silently returns empty descriptions. Price is
  found by scanning every `<span>` in the card for one whose own trimmed
  text starts with "$" - do not regex the card's full textContent for a
  price, since multi-price descriptions (e.g. "1 Cookie Cup: $4.50\nPick 4
  Cookie Cups: $15.99") will false-match the description instead.
- "List" layout: cards are `div[role="button"][data-item-modal-trigger-for]`
  with no separate tile-container id; the durable item id is the first
  segment of that trigger attribute, before "-CALC_". Description is
  whatever `<span>` immediately follows the `<h3>` name (absent entirely
  when there is no description, e.g. sold-out items on this layout).

Both layouts group cards under an enclosing `[data-testid^="menu-item-grid-"]`
section with an `<h2>` title. All items were mounted at once on every
restaurant sampled - no scroll-driven lazy loading observed here, unlike
DoorDash/Grubhub/Square - so this only scrolls once as a cheap safety net
for larger menus rather than polling for stability.

Sold-out detection: a card containing "Sold out" text (case-insensitive) or
a disabled `button[data-testid^="item-tile-add-"]` (tile layout only) is
flagged `is_sold_out` and its price is not trusted even if a stray $-span
is found. See external-data/menu-scraping/sold-out-detection-notes.md.

Requires the camofox-browser server already running (see the
camofox-startup skill / `camofox server start`).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

EXTRACT_JS = r"""
(function() {
  function extractTileCard(card) {
    const nameEl = card.querySelector('h3');
    const name = nameEl ? nameEl.textContent.trim() : '';
    const infoWrapper = card.lastElementChild;
    const descEl = infoWrapper ? infoWrapper.querySelector(':scope > span') : null;
    const description = descEl ? descEl.textContent.trim() : '';
    const spans = Array.from(card.querySelectorAll('span'));
    const priceSpan = spans.find(function(s) { return /^\$\d/.test(s.textContent.trim()); });
    const price = priceSpan ? priceSpan.textContent.trim() : null;
    const addButton = card.querySelector('button[data-testid^="item-tile-add-"]');
    const isSoldOut = /sold out/i.test(card.textContent) || (addButton ? addButton.disabled : false);
    const testid = card.getAttribute('data-testid') || '';
    const itemId = testid.replace('item-tile-container-', '');
    return { item_id: itemId, name: name, description: description, price: price, is_sold_out: isSoldOut };
  }

  function extractListCard(card) {
    const nameEl = card.querySelector('h3');
    const name = nameEl ? nameEl.textContent.trim() : '';
    let description = '';
    const afterName = nameEl ? nameEl.nextElementSibling : null;
    if (afterName && afterName.tagName === 'SPAN') {
      description = afterName.textContent.trim();
    }
    const isSoldOut = /sold out/i.test(card.textContent);
    const priceMatch = card.textContent.match(/\$[\d,]+\.\d{2}\+?/);
    const price = isSoldOut ? null : (priceMatch ? priceMatch[0] : null);
    const trigger = card.getAttribute('data-item-modal-trigger-for') || '';
    const itemId = trigger.split('-CALC_')[0] || trigger;
    return { item_id: itemId, name: name, description: description, price: price, is_sold_out: isSoldOut };
  }

  const sections = Array.from(document.querySelectorAll('[data-testid^="menu-item-grid-"]'));
  const results = [];
  for (const section of sections) {
    const headingEl = section.querySelector('h2');
    const sectionName = headingEl ? headingEl.textContent.trim() : (section.getAttribute('data-testid') || '').replace(/^menu-item-grid-/, '');
    const tileCards = Array.from(section.querySelectorAll('[data-testid^="item-tile-container-"]'));
    const cards = tileCards.length
      ? tileCards
      : Array.from(section.querySelectorAll('div[role="button"][data-item-modal-trigger-for]'));
    for (const card of cards) {
      const isTile = card.hasAttribute('data-testid') && card.getAttribute('data-testid').indexOf('item-tile-container-') === 0;
      const parsed = isTile ? extractTileCard(card) : extractListCard(card);
      if (!parsed.name) continue;
      parsed.section = sectionName;
      results.push(parsed);
    }
  }
  return JSON.stringify(results);
})()
""".strip()

ITEM_COUNT_JS = (
    'document.querySelectorAll(\'[data-testid^="item-tile-container-"], '
    'div[role="button"][data-item-modal-trigger-for]\').length'
)


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
            resp = requests.get(f"{self.server}/health", timeout=5)
            return resp.ok
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
        resp = requests.get(
            f"{self.server}/tabs/{tab_id}/screenshot",
            params={"userId": self.user_id},
            timeout=30,
        )
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

        if args.screenshot:
            shot = client.screenshot(tab_id)
            if shot:
                Path(args.screenshot).write_bytes(shot)

        before = client.evaluate(tab_id, ITEM_COUNT_JS) or 0
        client.evaluate(tab_id, "window.scrollTo(0, document.body.scrollHeight); null")
        time.sleep(1.5)
        after = client.evaluate(tab_id, ITEM_COUNT_JS) or 0
        if after > before:
            print(f"  note: item count grew after scroll ({before} -> {after}); menu may lazy-load more than a single scroll captures", file=sys.stderr)

        entries = client.evaluate(tab_id, EXTRACT_JS) or []
        final_url = client.evaluate(tab_id, "location.href")
    finally:
        client.close_tab(tab_id)
        client.close_session()

    output = {
        "source_url": args.url,
        "final_url": final_url,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "result": entries,
    }
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    section_count = len({e["section"] for e in entries if e.get("section")})
    sold_out_count = sum(1 for e in entries if e.get("is_sold_out"))
    print(f"Wrote {args.output} ({section_count} sections, {len(entries)} items, {sold_out_count} sold out)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url", help="Cash App order page, e.g. https://cash.app/$<seller>/l/<location-id>/pickup")
    parser.add_argument("output", type=Path)
    parser.add_argument("--latitude", type=float, default=42.197513)
    parser.add_argument("--longitude", type=float, default=-83.269677)
    parser.add_argument("--timezone", default="America/Detroit")
    parser.add_argument("--server", default="http://localhost:9377")
    parser.add_argument("--user", default="cashapp-scraper", help="camofox-browser profile id")
    parser.add_argument("--screenshot", type=Path, default=None, help="optional path to save an evidence screenshot")
    args = parser.parse_args()
    scrape(args)


if __name__ == "__main__":
    main()
