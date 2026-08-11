#!/usr/bin/env python3
"""Scrape a Clover Online Ordering menu via a running camofox-browser server.

Checked https://alex-kabob-house-southgate.cloveronline.com/menu/all for
JSON-LD/embedded state first (no `application/ld+json` scripts, no
`__NEXT_DATA__`, nothing on `window` that looked like a state dump) - Clover
appears to render everything client-side with no structured-data shortcut,
so this script falls back to DOM scraping. It still checks for JSON-LD at
runtime (see `try_jsonld_menu`) in case some other Clover deployment does
embed schema.org markup, since that would be far less brittle than the DOM
path if it's ever present.

On load, a "<restaurant> isn't accepting online orders right now" modal can
cover the page (same close button markup as the item modifier modal below -
`button[aria-label="Close modal"]`). It only needs dismissing once per
browser profile - confirmed it does not reappear on subsequent full page
navigations within the same session - but this script checks for it before
every page load anyway since that's cheap and safer than assuming.

Some items list at $0.00 in the plain item grid because the real price only
shows up after opening the item and choosing a required modifier (e.g. a
soup's Cup/Bowl/Quart size). This script does not resolve that pricing here
- it only captures the raw modifier groups for every $0.00-priced item by
navigating to each one's own `/menu/<slug>` URL (a normal link, not a
modal-only state, so this is a real navigation rather than a simulated
click) and reading the modal's modifier groups off the DOM. The actual
lowest-price/common-price/description logic lives in parse_clover_menu.py,
kept separate so the pricing rules can be tested without a browser.

Each modifier group is `[data-testid="modifier-group-display"]` wrapping a
`div[id=<groupId>]` with two children: a header row (group name text plus
an optional `[data-testid="modifier-group-rule-<groupId>"]` badge like "1
required") and an options container of `<label>` rows, each with an
`input[data-testid="modifier-input-<id>"]` (type radio or checkbox) and a
`[data-testid="modifier-price-<id>"]` span holding "+$X.XX". Some groups
have no rule badge at all (e.g. a "NO <ingredient>" removal checklist) -
those are optional and read here the same way; parse_clover_menu.py is the
one that decides which groups affect price.

Not every $0.00 item has a modifier group that explains the price - a few
(e.g. "Fried Kibbee 5 Pc") open a modal with zero modifier groups at all,
genuinely priced at $0.00 in the restaurant's own catalog. Captured as an
empty group list; parse_clover_menu.py flags those for manual review rather
than guessing at a price.

The whole menu (119 items on the sampled restaurant) is mounted at once on
`/menu/all` with no virtualization observed, so the base item list is a
single DOM pass.

Every click/navigation here is preceded by a randomized human-paced delay -
a tight loop of instant navigations/clicks (this script visits one page per
$0.00 item) is a much easier bot signal to spot than the couple of seconds
of jitter this adds.

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
from urllib.parse import urljoin

import requests

JSONLD_RAW_JS = r"""
JSON.stringify(Array.from(document.querySelectorAll('script[type="application/ld+json"]')).map(s => s.textContent))
""".strip()

EXTRACT_BASE_MENU_JS = r"""
(function() {
  const headers = Array.from(document.querySelectorAll('h2'));
  const cards = Array.from(document.querySelectorAll('[data-testid="single-product"]'));
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
    const a = card.closest('a');
    const nameEl = card.querySelector('[data-testid="item-name"]');
    const priceEl = card.querySelector('[data-testid="product-price"]');
    const descEl = card.querySelector('[data-testid="product-description"]');
    results.push({
      section: current,
      name: nameEl ? nameEl.textContent.trim() : null,
      price: priceEl ? priceEl.textContent.trim() : null,
      description: descEl ? descEl.textContent.trim() : '',
      href: a ? a.getAttribute('href') : null,
    });
  }
  return JSON.stringify(results);
})()
""".strip()

EXTRACT_MODIFIERS_JS = r"""
(function() {
  const displays = Array.from(document.querySelectorAll('[data-testid="restaurant-menu-page-item"] [data-testid="modifier-group-display"]'));
  return JSON.stringify(displays.map(function(display) {
    const groupDiv = display.children[0];
    const headerRow = groupDiv.children[0];
    const optionsContainer = groupDiv.children[1];
    const badge = headerRow.querySelector('[data-testid^="modifier-group-rule-"]');
    const nameCandidate = Array.from(headerRow.children).find(function(c) { return c !== badge; });
    const groupName = nameCandidate ? nameCandidate.textContent.trim() : '';
    const ruleText = badge ? badge.textContent.trim() : null;
    const options = Array.from(optionsContainer.querySelectorAll('input[data-testid^="modifier-input-"]')).map(function(input) {
      const label = input.closest('label');
      const priceEl = label.querySelector('[data-testid^="modifier-price-"]');
      const nameEl = input.parentElement.querySelector('div');
      return {
        name: nameEl ? nameEl.textContent.trim() : '',
        price_text: priceEl ? priceEl.textContent.trim() : '',
        input_type: input.type,
      };
    });
    return { group_id: groupDiv.id, group_name: groupName, rule_text: ruleText, options: options };
  }));
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

    def navigate(self, tab_id: str, url: str) -> bool:
        """Best-effort navigate - Clover's SPA router sometimes intercepts a
        freshly-issued navigation (NS_BINDING_ABORTED) even though the route
        still ends up changing correctly, so a failure here isn't fatal;
        callers proceed to check for the expected post-navigation state
        regardless."""
        try:
            self._post(f"/tabs/{tab_id}/navigate", {"url": url})
            return True
        except requests.RequestException:
            return False

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

    def wait_for_selector(self, tab_id: str, selector: str, timeout_ms: int = 8000, poll_ms: int = 300) -> bool:
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
    """Pause like someone reading the page before their next click/navigation."""
    time.sleep(random.uniform(min_s, max_s))


def close_modal_if_present(client: CamofoxClient, tab_id: str, timeout_ms: int = 3000) -> bool:
    if not client.wait_for_selector(tab_id, 'button[aria-label="Close modal"]', timeout_ms=timeout_ms, poll_ms=250):
        return False
    human_delay(0.5, 1.4)
    return client.click(tab_id, 'button[aria-label="Close modal"]')


def try_jsonld_menu(client: CamofoxClient, tab_id: str) -> list[dict[str, Any]] | None:
    """Best-effort schema.org extraction, unverified against a live Clover
    site (none seen with JSON-LD during this script's development) - only
    used if it actually finds menu items, otherwise the caller falls back
    to the DOM path that's actually been tested."""
    raw_scripts = client.evaluate(tab_id, JSONLD_RAW_JS) or []
    if not raw_scripts:
        return None
    parsed = []
    for raw in raw_scripts:
        try:
            parsed.append(json.loads(raw))
        except json.JSONDecodeError:
            continue

    def flatten(value: Any) -> list[dict[str, Any]]:
        if isinstance(value, dict):
            return [value]
        if isinstance(value, list):
            out: list[dict[str, Any]] = []
            for v in value:
                out.extend(flatten(v))
            return out
        return []

    restaurant = next((p for p in parsed if isinstance(p, dict) and p.get("@type") == "Restaurant"), None)
    menu = restaurant.get("hasMenu") if restaurant else None
    if not menu:
        menu = next((p for p in parsed if isinstance(p, dict) and p.get("@type") == "Menu"), None)
    if not menu:
        return None

    items: list[dict[str, Any]] = []
    for section in flatten(menu.get("hasMenuSection", [])):
        section_name = section.get("name") or ""
        for item in flatten(section.get("hasMenuItem", [])):
            name = item.get("name")
            if not name:
                continue
            offers = item.get("offers")
            price = None
            if isinstance(offers, dict) and offers.get("price") is not None:
                price = f"${offers['price']}"
            items.append(
                {
                    "section": section_name,
                    "name": name,
                    "price": price,
                    "description": item.get("description") or "",
                    "href": None,
                }
            )
    return items or None


def scrape(args: argparse.Namespace) -> None:
    client = CamofoxClient(args.server, args.user)
    if not client.health():
        print(f"camofox-browser server not reachable at {args.server}. Start it first (camofox-startup skill).", file=sys.stderr)
        sys.exit(2)

    tab_id = client.open_tab(args.url, args.latitude, args.longitude, args.timezone)
    try:
        client.wait(tab_id, timeout_ms=15000)
        human_delay(1.5, 2.5)
        close_modal_if_present(client, tab_id)

        json_ld_items = try_jsonld_menu(client, tab_id)
        json_ld_used = json_ld_items is not None
        items = json_ld_items if json_ld_used else (client.evaluate(tab_id, EXTRACT_BASE_MENU_JS) or [])

        zero_price_items = [
            it for it in items if it.get("href") and (it.get("price") is None or it.get("price") == "$0.00")
        ]

        modifiers: dict[str, list[dict[str, Any]]] = {}
        for it in zero_price_items:
            human_delay()
            item_url = urljoin(args.url, it["href"])
            client.navigate(tab_id, item_url)
            if not client.wait_for_selector(tab_id, '[data-testid="item-modal-name"]', timeout_ms=8000):
                # Modal didn't open the way every sampled item did - leave this
                # item's modifiers empty rather than guessing; parse_clover_menu.py
                # will flag it for manual review same as a genuinely modifier-less item.
                modifiers[it["href"]] = []
                continue
            time.sleep(0.5)
            modifiers[it["href"]] = client.evaluate(tab_id, EXTRACT_MODIFIERS_JS) or []
            # Deliberately not clicking the close button here: it navigates
            # the SPA back to the listing page (each item modal is its own
            # route), and that in-flight navigation races with the next
            # item's navigate() below - it intermittently ate the whole next
            # item's modifier data, which is why this loop just moves
            # straight to the next item's URL instead.

        final_url = client.evaluate(tab_id, "location.href")
    finally:
        client.close_tab(tab_id)
        client.close_session()

    output = {
        "source_url": args.url,
        "final_url": final_url,
        "json_ld_used": json_ld_used,
        "items": items,
        "modifiers": modifiers,
    }
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    section_count = len({it["section"] for it in items if it.get("section")})
    print(
        f"Wrote {args.output} ({section_count} sections, {len(items)} items, "
        f"json_ld_used={json_ld_used}, {len(zero_price_items)} $0.00 items checked for modifiers)"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url", help="Clover menu page, e.g. https://<slug>.cloveronline.com/menu/all")
    parser.add_argument("output", type=Path)
    parser.add_argument("--latitude", type=float, default=42.197513)
    parser.add_argument("--longitude", type=float, default=-83.269677)
    parser.add_argument("--timezone", default="America/Detroit")
    parser.add_argument("--server", default="http://localhost:9377")
    parser.add_argument("--user", default="clover-scraper", help="camofox-browser profile id")
    args = parser.parse_args()
    scrape(args)


if __name__ == "__main__":
    main()
