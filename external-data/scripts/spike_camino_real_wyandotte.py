#!/usr/bin/env python3
"""Spike raw text menu/source collection for Camino Real Wyandotte."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, unquote, urljoin, urlparse, parse_qs

from bs4 import BeautifulSoup
from camoufox.sync_api import Camoufox


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "external-data/menu-scraping/camino_real_wyandotte_spike"
DEFAULT_LOCATION = {
    "latitude": 42.19351025,
    "longitude": -83.1795100375,
}
TARGET = {
    "name": "Camino Real Mexican Grill",
    "address": "3851 Fort Street, Wyandotte, MI 48192",
    "city": "Wyandotte",
    "state": "MI",
    "website": "https://www.restaurantcaminoreal.com/",
}
PROVIDER_PATTERNS = [
    "doordash.com",
    "grubhub.com",
    "ubereats.com",
    "toasttab.com",
    "clover.com",
    "square.site",
    "order.online",
    "menufy.com",
    "beyondmenu.com",
    "chownow.com",
    "ezcater.com",
    "slice.life",
    "seamless.com",
]
USEFUL_LINK_RE = re.compile(
    r"(menu|order|online|about|location|contact|hours|catering|gallery|dinner|lunch)",
    re.I,
)
MENU_TEXT_RE = re.compile(
    r"(\$\d|taco|burrito|enchilada|fajita|quesadilla|nacho|chimichanga|"
    r"menu|lunch|dinner|appetizer|dessert|drink|margarita|salsa|guacamole)",
    re.I,
)


@dataclass
class SavedPage:
    source: str
    url: str
    final_url: str
    title: str
    html_path: str | None
    text_path: str
    screenshot_path: str
    text_chars: int
    looks_menuish: bool
    provider_links: list[str]


def slug(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return cleaned[:90] or "page"


def unwrap_google_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.path == "/url":
        qs = parse_qs(parsed.query)
        if qs.get("q"):
            return qs["q"][0]
    return url


def clean_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for node in soup(["script", "style", "noscript", "svg"]):
        node.decompose()
    text = soup.get_text("\n")
    lines = []
    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            lines.append(line)
    deduped = []
    seen = set()
    for line in lines:
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(line)
    return "\n".join(deduped) + "\n"


def title_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    return soup.title.get_text(" ", strip=True) if soup.title else ""


def provider_links_from_html(html: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    found: list[str] = []
    for tag in soup.find_all(["a", "form"]):
        href = tag.get("href") or tag.get("action")
        if not href:
            continue
        href = unquote(str(href))
        if any(pattern in href.lower() for pattern in PROVIDER_PATTERNS):
            if href not in found:
                found.append(href)
    return found


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


def save_page(page: Any, source: str, url: str, out_dir: Path) -> SavedPage:
    page.goto(url, wait_until="domcontentloaded", timeout=70000)
    page.wait_for_timeout(3500)
    close_known_modals(page)
    page.mouse.wheel(0, 1800)
    page.wait_for_timeout(1000)
    html = page.content()
    final_url = page.url
    digest = hashlib.sha1(final_url.encode()).hexdigest()[:10]
    stem = f"{slug(source)}-{slug(urlparse(final_url).path or urlparse(final_url).netloc)}-{digest}"
    html_path = out_dir / f"{stem}.html"
    text_path = out_dir / f"{stem}.txt"
    screenshot_path = out_dir / f"{stem}.png"
    text = clean_text(html)
    if len(html.encode("utf-8")) <= 5_000_000:
        html_path.write_text(html, encoding="utf-8")
        html_rel: str | None = str(html_path.relative_to(ROOT))
    else:
        html_rel = None
    text_path.write_text(text, encoding="utf-8")
    page.screenshot(path=str(screenshot_path), full_page=True)
    return SavedPage(
        source=source,
        url=url,
        final_url=final_url,
        title=title_from_html(html),
        html_path=html_rel,
        text_path=str(text_path.relative_to(ROOT)),
        screenshot_path=str(screenshot_path.relative_to(ROOT)),
        text_chars=len(text),
        looks_menuish=bool(MENU_TEXT_RE.search(text)),
        provider_links=provider_links_from_html(html),
    )


def same_site(url: str, base: str) -> bool:
    return urlparse(url).netloc.lower().removeprefix("www.") == urlparse(base).netloc.lower().removeprefix("www.")


def official_site_links(page: Any, base_url: str) -> list[str]:
    links = page.locator("a").evaluate_all("els => els.map(a => a.href).filter(Boolean)")
    useful: list[str] = [base_url]
    for link in links:
        target = urljoin(base_url, link)
        if not same_site(target, base_url):
            continue
        if USEFUL_LINK_RE.search(target) and target not in useful:
            useful.append(target)
    return useful[:14]


def google_search_links(page: Any, query: str) -> list[str]:
    page.goto(f"https://www.google.com/search?q={quote_plus(query)}", wait_until="domcontentloaded", timeout=70000)
    page.wait_for_timeout(4000)
    links = page.locator("a").evaluate_all("els => els.map(a => a.href).filter(Boolean)")
    found: list[str] = []
    for link in links:
        target = unquote(unwrap_google_url(link))
        if target.startswith("http") and target not in found:
            found.append(target)
    return found


def marketplace_candidates(page: Any) -> dict[str, list[str]]:
    queries = {
        "google_order_panel": f"{TARGET['name']} {TARGET['address']} order online",
        "doordash": f"site:doordash.com/store {TARGET['name']} {TARGET['city']} MI",
        "grubhub": f"site:grubhub.com/restaurant {TARGET['name']} {TARGET['city']} MI",
        "uber_eats": f"site:ubereats.com {TARGET['name']} {TARGET['city']} MI",
    }
    candidates: dict[str, list[str]] = {}
    for source, query in queries.items():
        links = google_search_links(page, query)
        if source == "google_order_panel":
            candidates[source] = [
                link for link in links if any(pattern in link.lower() for pattern in PROVIDER_PATTERNS)
            ][:12]
        elif source == "doordash":
            candidates[source] = [link for link in links if "doordash.com/store" in link.lower()][:6]
        elif source == "grubhub":
            candidates[source] = [link for link in links if "grubhub.com/restaurant" in link.lower()][:6]
        elif source == "uber_eats":
            candidates[source] = [link for link in links if "ubereats.com" in link.lower()][:6]
        time.sleep(1)
    return candidates


def direct_marketplace_urls() -> dict[str, list[str]]:
    query = quote_plus(f"{TARGET['name']} {TARGET['city']} MI")
    return {
        "doordash_direct_search": [f"https://www.doordash.com/search/store/{query}/"],
        "grubhub_direct_search": [f"https://www.grubhub.com/search?searchText={query}"],
        "uber_eats_direct_search": [f"https://www.ubereats.com/search?q={query}"],
    }


def combine_menu_text(saved_pages: list[SavedPage], out_dir: Path) -> Path:
    combined = out_dir / "camino-real-wyandotte-raw-menu-and-restaurant-text.txt"
    chunks = [
        "# Camino Real Mexican Grill Wyandotte Raw Menu and Restaurant Text",
        "",
        f"Target: {TARGET['name']}",
        f"Address: {TARGET['address']}",
        f"Official site: {TARGET['website']}",
        "",
    ]
    for saved in saved_pages:
        text = (ROOT / saved.text_path).read_text(encoding="utf-8", errors="replace")
        include = saved.source == "official_site"
        include = include or (
            saved.source == "official_site_provider_links"
            and "Camino Real Mexican Grill (Fort St)" in text
        )
        provider_url = saved.final_url.lower()
        include = include or (
            saved.source == "google_order_panel"
            and saved.looks_menuish
            and (
                "custom.order.online" in provider_url
                or "grubhub.com/restaurant" in provider_url
                or "doordash.com/en/store" in provider_url
                or "ubereats.com/store" in provider_url
            )
        )
        if not include:
            continue
        chunks.extend(
            [
                "",
                "============================================================",
                f"Source: {saved.source}",
                f"URL: {saved.final_url}",
                f"Title: {saved.title}",
                "============================================================",
                "",
                text,
            ]
        )
    combined.write_text("\n".join(chunks), encoding="utf-8")
    return combined


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--latitude", type=float, default=DEFAULT_LOCATION["latitude"])
    parser.add_argument("--longitude", type=float, default=DEFAULT_LOCATION["longitude"])
    parser.add_argument("--headful", action="store_true")
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    saved_pages: list[SavedPage] = []
    notes: dict[str, Any] = {
        "target": TARGET,
        "geolocation": {"latitude": args.latitude, "longitude": args.longitude},
        "saved_pages": [],
        "marketplace_candidates": {},
        "errors": [],
    }
    discovered_provider_links: list[str] = []

    with Camoufox(headless=not args.headful, humanize=True) as browser:
        context = browser.new_context(
            viewport={"width": 1365, "height": 900},
            locale="en-US",
            timezone_id="America/Detroit",
            geolocation={"latitude": args.latitude, "longitude": args.longitude},
            permissions=["geolocation"],
        )
        page = context.new_page()
        try:
            print("Saving official site homepage", flush=True)
            home = save_page(page, "official_site", TARGET["website"], args.output)
            saved_pages.append(home)
            links = official_site_links(page, TARGET["website"])
            print(f"Found {len(links)} official-site candidate pages", flush=True)
            for link in links:
                if link == TARGET["website"]:
                    continue
                try:
                    print(f"Saving official site page: {link}", flush=True)
                    saved_pages.append(save_page(page, "official_site", link, args.output))
                except Exception as exc:
                    notes["errors"].append(f"official_site {link}: {type(exc).__name__}: {exc}")
            for saved in saved_pages:
                for provider_link in saved.provider_links:
                    if provider_link not in discovered_provider_links:
                        discovered_provider_links.append(provider_link)
        except Exception as exc:
            notes["errors"].append(f"official_site: {type(exc).__name__}: {exc}")

        try:
            print("Discovering marketplace/order candidates through Google", flush=True)
            candidates = marketplace_candidates(page)
            candidates["official_site_provider_links"] = discovered_provider_links
            candidates.update(direct_marketplace_urls())
            notes["marketplace_candidates"] = candidates
            for source, urls in candidates.items():
                limit = 8 if source == "google_order_panel" else 3
                for url in urls[:limit]:
                    try:
                        print(f"Saving {source}: {url}", flush=True)
                        saved_pages.append(save_page(page, source, url, args.output))
                    except Exception as exc:
                        notes["errors"].append(f"{source} {url}: {type(exc).__name__}: {exc}")
        except Exception as exc:
            notes["errors"].append(f"marketplace_discovery: {type(exc).__name__}: {exc}")
        context.close()

    notes["saved_pages"] = [asdict(saved) for saved in saved_pages]
    combined = combine_menu_text(saved_pages, args.output)
    notes["combined_text_path"] = str(combined.relative_to(ROOT))
    notes_path = args.output / "spike-notes.json"
    notes_path.write_text(json.dumps(notes, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {combined.relative_to(ROOT)}", flush=True)
    print(f"Wrote {notes_path.relative_to(ROOT)}", flush=True)


if __name__ == "__main__":
    main()
