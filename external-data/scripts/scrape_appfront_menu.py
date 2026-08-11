#!/usr/bin/env python3
"""Scrape an AppFront-powered restaurant ordering site's menu via a running
camofox-browser server.

AppFront (see .agents/skills/appfront-menu-scraper/SKILL.md) is white-labeled
onto each restaurant's own domain (e.g. order.middleeats.com), has no
JSON-LD, and needs multi-step navigation to reach a menu:

  homepage -> "Start New Order" -> "Pickup"/"Delivery" -> (location picker,
  multi-location businesses only) -> the actual menu.

Single-location businesses skip the location picker entirely and land
straight on the menu after choosing a serving option, so this script detects
which happened rather than assuming either path.

Items have no durable id in the card markup - only `aria-label="<name>"`.
A stable id only appears in the URL after clicking an item open
(`/order/items/<id>/...`), which would mean one navigation per item to
collect - too expensive to do for every item on a full menu, so the
"Best Sellers" rollup category (same duplicate-category pattern as Uber
Eats/DoorDash/Grubhub) is folded into its real category by exact name match
instead. That's a known weak point: two differently-configured items that
happen to share a name would incorrectly merge. Verified for one restaurant
(Middle Eats, Southgate) that produced 5/5 clean matches.

Every click here is preceded by a randomized human-paced delay - a tight
loop of instant navigations/clicks is a much easier bot signal to spot than
the couple of seconds of jitter this adds.

Requires the camofox-browser server already running (see the camofox-startup
skill / `camofox server start`).
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from pathlib import Path
from typing import Any

import requests

EXTRACT_MENU_JS = r"""
(function() {
  const headers = Array.from(document.querySelectorAll('h2, h3'))
    .filter(function(h) { return !h.closest('[class*="CategoryItem"]'); });
  const items = Array.from(document.querySelectorAll('[class*="CategoryItem"][aria-label]'));
  const all = [
    ...headers.map(function(h) { return { type: 'header', el: h, text: h.textContent.trim() }; }),
    ...items.map(function(i) { return { type: 'item', el: i }; }),
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
    const name = card.getAttribute('aria-label');
    const descEl = card.querySelector('[class*="ListCardDescription"]');
    const titleRow = card.querySelector('[class*="ListCardTitle"]');
    let price = null;
    if (titleRow) {
      const priceMatch = titleRow.textContent.match(/\$\d[\d.,]*\+?/);
      price = priceMatch ? priceMatch[0] : null;
    }
    results.push({
      section: current,
      name: name,
      description: descEl ? descEl.textContent.trim() : '',
      price: price,
    });
  }
  return JSON.stringify(results);
})()
""".strip()

IS_APPFRONT_JS = r"""
JSON.stringify({
  metaHit: Array.from(document.querySelectorAll('meta')).some(function(m) { return (m.content || '').includes('.appfront.app'); }),
  poweredByLink: !!document.querySelector('a[href*="appfront.ai"]'),
})
""".strip()

HAS_ITEMS_JS = 'document.querySelectorAll(\'[class*="CategoryItem"][aria-label]\').length > 0'

COLLECT_BRANCH_LINKS_JS = r"""
JSON.stringify(Array.from(document.querySelectorAll('a[href*="branchId"]')).map(function(a) {
  const url = new URL(a.getAttribute('href'), location.origin);
  return {
    branch_name: url.searchParams.get('branchName'),
    branch_id: url.searchParams.get('branchId'),
    href: url.toString(),
  };
}))
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


def is_appfront_site(client: CamofoxClient, tab_id: str) -> bool:
    result = client.evaluate(tab_id, IS_APPFRONT_JS) or {}
    return bool(result.get("metaHit") or result.get("poweredByLink"))


def click_by_text(client: CamofoxClient, tab_id: str, text: str, timeout_ms: int = 10000, poll_ms: int = 400) -> bool:
    """Retry an exact-text click (Playwright's `text="..."` selector engine,
    same semantics as get_by_text(text, exact=True)) until it succeeds or the
    timeout elapses - the underlying /click call already waits up to 5s per
    attempt for the element to become actionable, so this just covers the
    case where the element hasn't even been rendered yet.

    This page renders the same-text control twice (a responsive mobile/
    desktop pair) - confirmed live that which copy is visible depends on the
    profile's randomized viewport, not DOM order, so `>> visible=true`
    disambiguates by actual visibility instead of an index like `.first`/
    `nth=0`, which would pick the hidden copy on some viewports."""
    selector = f'text="{text}" >> visible=true'
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        human_delay(0.5, 1.4)
        if client.click(tab_id, selector):
            return True
        time.sleep(poll_ms / 1000)
    return False


def collect_branch_links(client: CamofoxClient, tab_id: str) -> list[dict[str, str]]:
    return client.evaluate(tab_id, COLLECT_BRANCH_LINKS_JS) or []


def navigate_to_menu(
    client: CamofoxClient, tab_id: str, serving_option: str, branch_name: str | None
) -> dict[str, Any]:
    """Return {"branch_name": ..., "branch_id": ..., "single_location": bool}.
    Assumes the tab is already sitting on the restaurant's AppFront homepage."""
    if not click_by_text(client, tab_id, "Start New Order"):
        raise RuntimeError("Could not find 'Start New Order' - page layout may differ from what this script expects")
    time.sleep(1.0)

    option_label = serving_option.capitalize()
    if not click_by_text(client, tab_id, option_label):
        raise RuntimeError(f"Could not find serving option '{option_label}'")
    time.sleep(1.5)

    # Single-location businesses skip straight to the menu; multi-location
    # ones land on /find-location/ with a branch list. Detect which by
    # checking for menu item cards vs. branch links.
    has_items = bool(client.evaluate(tab_id, HAS_ITEMS_JS))
    if has_items:
        current_url = client.evaluate(tab_id, "location.href") or ""
        match = re.search(r"branchId=([^&]+).*branchName=([^&]+)", current_url)
        return {
            "single_location": True,
            "branch_id": match.group(1) if match else None,
            "branch_name": match.group(2) if match else None,
        }

    branches = collect_branch_links(client, tab_id)
    if not branches:
        raise RuntimeError("Landed on neither a menu nor a recognizable branch list - page layout may have changed")

    if branch_name is not None:
        chosen = next((b for b in branches if b["branch_name"] == branch_name), None)
        if chosen is None:
            available = ", ".join(b["branch_name"] for b in branches)
            raise RuntimeError(f"Branch '{branch_name}' not found. Available: {available}")
    else:
        # Branch list is sorted by distance from the browser's geolocation.
        chosen = branches[0]

    human_delay()
    client.navigate(tab_id, chosen["href"])
    client.wait(tab_id, timeout_ms=15000)
    time.sleep(2.0)
    return {
        "single_location": False,
        "branch_id": chosen["branch_id"],
        "branch_name": chosen["branch_name"],
    }


def scrape(args: argparse.Namespace) -> None:
    client = CamofoxClient(args.server, args.user)
    if not client.health():
        print(f"camofox-browser server not reachable at {args.server}. Start it first (camofox-startup skill).", file=sys.stderr)
        sys.exit(2)

    tab_id = client.open_tab(args.url, args.latitude, args.longitude, args.timezone)
    try:
        client.wait(tab_id, timeout_ms=15000)
        human_delay(1.2, 2.0)

        if not is_appfront_site(client, tab_id):
            print(f"{args.url} does not look like an AppFront site (no matching meta tag or Powered-by link)", file=sys.stderr)
            sys.exit(2)

        branch_info = navigate_to_menu(client, tab_id, args.serving_option, args.branch_name)
        entries = client.evaluate(tab_id, EXTRACT_MENU_JS) or []
        final_url = client.evaluate(tab_id, "location.href")
    finally:
        client.close_tab(tab_id)
        client.close_session()

    output = {
        "source_url": args.url,
        "final_url": final_url,
        "branch": branch_info,
        "result": entries,
    }
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    section_count = len({e["section"] for e in entries})
    print(f"Wrote {args.output} ({section_count} sections, {len(entries)} items, branch={branch_info['branch_name']!r})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url", help="AppFront restaurant homepage, e.g. https://order.middleeats.com/a")
    parser.add_argument("output", type=Path)
    parser.add_argument("--serving-option", choices=["pickup", "delivery"], default="pickup")
    parser.add_argument("--branch-name", default=None, help="Exact branch name to pick; defaults to the closest one")
    parser.add_argument("--latitude", type=float, default=42.197513)
    parser.add_argument("--longitude", type=float, default=-83.269677)
    parser.add_argument("--timezone", default="America/Detroit")
    parser.add_argument("--server", default="http://localhost:9377")
    parser.add_argument("--user", default="appfront-scraper", help="camofox-browser profile id")
    args = parser.parse_args()
    scrape(args)


if __name__ == "__main__":
    main()
