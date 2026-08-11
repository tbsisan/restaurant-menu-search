#!/usr/bin/env python3
"""Find Camino Real Wyandotte ordering providers from Google and open Grubhub."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, unquote, urlparse

from bs4 import BeautifulSoup
from camoufox.sync_api import Camoufox


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "external-data/menu-scraping/camino_real_wyandotte_grubhub_spike"
TARGET = {
    "name": "Camino Real Mexican Grill",
    "address": "3851 Fort Street, Wyandotte, MI 48192",
    "latitude": 42.19351025,
    "longitude": -83.1795100375,
}
PROVIDER_PATTERNS = (
    "grubhub.com",
    "doordash.com",
    "custom.order.online",
    "order.online",
    "ubereats.com",
)


def slug(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()[:90] or "page"


def clean_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for node in soup(["script", "style", "noscript", "svg"]):
        node.decompose()
    lines: list[str] = []
    for line in soup.get_text("\n").splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines) + "\n"


def title_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    return soup.title.get_text(" ", strip=True) if soup.title else ""


def close_known_modals(page: Any) -> None:
    """Dismiss platform "store is closed" dialogs that would otherwise sit on
    top of the menu. Grubhub blocks with a real modal ("Schedule my order")
    when the restaurant is outside business hours, closed via a back-arrow
    button (testid below, not an X) - confirmed live against Camino Real
    Wyandotte while it was actually closed. Uber Eats/DoorDash instead show
    a non-blocking inline banner, so there's nothing to dismiss for those."""
    try:
        page.locator('[data-testid="close-cart-edit-modal"]').first.click(timeout=2000)
    except Exception:
        pass


def save_page(page: Any, source: str, out_dir: Path) -> dict[str, Any]:
    page.wait_for_timeout(2500)
    close_known_modals(page)
    html = page.content()
    text = clean_text(html)
    final_url = page.url
    digest = hashlib.sha1(final_url.encode()).hexdigest()[:10]
    stem = f"{slug(source)}-{slug(urlparse(final_url).netloc + urlparse(final_url).path)}-{digest}"
    html_path = out_dir / f"{stem}.html"
    txt_path = out_dir / f"{stem}.txt"
    png_path = out_dir / f"{stem}.png"
    html_path.write_text(html, encoding="utf-8")
    txt_path.write_text(text, encoding="utf-8")
    page.screenshot(path=str(png_path), full_page=True)
    return {
        "source": source,
        "url": final_url,
        "title": title_from_html(html),
        "html_path": str(html_path.relative_to(ROOT)),
        "text_path": str(txt_path.relative_to(ROOT)),
        "screenshot_path": str(png_path.relative_to(ROOT)),
        "text_chars": len(text),
    }


def links(page: Any) -> list[dict[str, str]]:
    return page.locator("a").evaluate_all(
        """els => els.map(a => ({
            href: a.href || "",
            text: (a.innerText || a.getAttribute("aria-label") || "").trim()
        })).filter(x => x.href)"""
    )


def provider_links(page: Any) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    seen: set[str] = set()
    for link in links(page):
        href = unquote(link["href"])
        if any(pattern in href.lower() for pattern in PROVIDER_PATTERNS) and href not in seen:
            seen.add(href)
            found.append({"href": href, "text": link.get("text", "")})
    return found


def click_order_surface(page: Any) -> list[str]:
    clicked: list[str] = []
    labels = [
        "Order online",
        "Order pickup",
        "Order delivery",
        "Order",
    ]
    for label in labels:
        loc = page.get_by_text(label, exact=False).first
        try:
            if loc.count() == 0:
                continue
            loc.click(timeout=5000)
            page.wait_for_timeout(4000)
            clicked.append(label)
            break
        except Exception:
            continue
    return clicked


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--headful", action="store_true")
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    notes: dict[str, Any] = {
        "target": TARGET,
        "geolocation": {
            "latitude": TARGET["latitude"],
            "longitude": TARGET["longitude"],
        },
        "search_query": TARGET["name"],
        "saved_pages": [],
        "provider_links": [],
        "chosen_grubhub_url": "",
        "errors": [],
    }

    with Camoufox(headless=not args.headful, humanize=True) as browser:
        context = browser.new_context(
            viewport={"width": 1365, "height": 900},
            locale="en-US",
            timezone_id="America/Detroit",
            geolocation={"latitude": TARGET["latitude"], "longitude": TARGET["longitude"]},
            permissions=["geolocation"],
        )
        page = context.new_page()
        search_url = f"https://www.google.com/search?q={quote_plus(TARGET['name'])}"
        page.goto(search_url, wait_until="domcontentloaded", timeout=70000)
        page.wait_for_timeout(6000)
        notes["saved_pages"].append(save_page(page, "google-search-restaurant-name", args.output))
        notes["provider_links"].extend(provider_links(page))

        clicked = click_order_surface(page)
        notes["clicked_order_surfaces"] = clicked
        notes["saved_pages"].append(save_page(page, "google-after-order-click", args.output))
        for link in provider_links(page):
            if link not in notes["provider_links"]:
                notes["provider_links"].append(link)

        grubhub_url = next(
            (link["href"] for link in notes["provider_links"] if "grubhub.com/restaurant" in link["href"].lower()),
            "",
        )
        if not grubhub_url:
            # Fallback to direct Grubhub restaurant URL discovered in the earlier order-panel spike.
            grubhub_url = "https://www.grubhub.com/restaurant/camino-real-mexican-grill-3851-fort-st-wyandotte/6882728"
        notes["chosen_grubhub_url"] = grubhub_url

        try:
            page.goto(grubhub_url, wait_until="domcontentloaded", timeout=70000)
            page.wait_for_timeout(7000)
            notes["saved_pages"].append(save_page(page, "grubhub-restaurant-page", args.output))
        except Exception as exc:
            notes["errors"].append(f"grubhub_open: {type(exc).__name__}: {exc}")
        context.close()

    notes_path = args.output / "spike-notes.json"
    notes_path.write_text(json.dumps(notes, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {notes_path.relative_to(ROOT)}")
    print(f"Chosen Grubhub URL: {notes['chosen_grubhub_url']}")


if __name__ == "__main__":
    main()
