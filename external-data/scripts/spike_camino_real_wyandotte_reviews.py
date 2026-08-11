#!/usr/bin/env python3
"""Spike review/rating collection for Camino Real Wyandotte."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

from bs4 import BeautifulSoup
from camoufox.sync_api import Camoufox


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "external-data/review-scraping/camino_real_wyandotte_spike"
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
REVIEW_SOURCE_PATTERNS = {
    "google_maps": ["google.com/maps", "maps.google.com"],
    "google_search": ["google.com/search"],
    "doordash": ["doordash.com", "order.online"],
    "grubhub": ["grubhub.com"],
    "postmates_uber_eats": ["postmates.com", "ubereats.com"],
    "yelp": ["yelp.com/biz"],
    "facebook": ["facebook.com"],
    "tripadvisor": ["tripadvisor.com"],
}
DIRECT_SOURCE_SEARCHES = {
    "google_search": f"{TARGET['name']} {TARGET['address']} reviews",
    "google_maps": f"{TARGET['name']} {TARGET['address']}",
    "doordash": f"site:doordash.com/store {TARGET['name']} {TARGET['city']} MI reviews rating",
    "grubhub": f"site:grubhub.com/restaurant {TARGET['name']} {TARGET['city']} MI reviews rating",
    "postmates_uber_eats": f"site:ubereats.com OR site:postmates.com {TARGET['name']} {TARGET['city']} MI reviews rating",
    "yelp": f"site:yelp.com/biz {TARGET['name']} {TARGET['city']} MI",
    "facebook": f"site:facebook.com {TARGET['name']} {TARGET['city']} MI reviews rating",
    "tripadvisor": f"site:tripadvisor.com {TARGET['name']} {TARGET['city']} MI",
}
DIRECT_URLS = {
    "official_site": [TARGET["website"]],
    "google_search": [
        f"https://www.google.com/search?q={quote_plus(DIRECT_SOURCE_SEARCHES['google_search'])}",
    ],
    "google_maps": [
        f"https://www.google.com/maps/search/{quote_plus(DIRECT_SOURCE_SEARCHES['google_maps'])}",
    ],
    "doordash": [
        "https://www.doordash.com/en/store/camino-real-mexican-grill-238625/",
        "https://custom.order.online/en-US/store/camino-real-mexican-grill-wyandotte-238625",
    ],
    "grubhub": [
        "https://www.grubhub.com/restaurant/camino-real-mexican-grill-3851-fort-st-wyandotte/6882728",
    ],
    "postmates_uber_eats": [
        "https://www.ubereats.com/store/camino-real-mexican-grill-wyandotte/QXhsSH0yVSeESCNVX6sQDQ",
    ],
}
RATING_RE = re.compile(
    r"(?P<rating>[1-5](?:\.\d)?)\s*(?:out of\s*)?(?:/|of)?\s*5\s*(?:stars?)?",
    re.I,
)
COUNT_RE = re.compile(r"(?P<count>\d[\d,]*)\s+(?:reviews?|ratings?)", re.I)
DATE_RE = re.compile(
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b"
    r"|\b\d+\s+(?:minute|hour|day|week|month|year)s?\s+ago\b",
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
    extracted: dict[str, Any]


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
    lines: list[str] = []
    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines) + "\n"


def title_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    return soup.title.get_text(" ", strip=True) if soup.title else ""


def jsonld_blocks(html: str) -> list[Any]:
    soup = BeautifulSoup(html, "lxml")
    blocks: list[Any] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text()
        if not raw.strip():
            continue
        try:
            blocks.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return blocks


def source_for_url(url: str, fallback: str = "google_search") -> str:
    lowered = url.lower()
    for source, patterns in REVIEW_SOURCE_PATTERNS.items():
        if any(pattern in lowered for pattern in patterns):
            return source
    return fallback


def extract_rating_candidates(text: str, html: str) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    for match in RATING_RE.finditer(text):
        start = max(0, match.start() - 120)
        end = min(len(text), match.end() + 180)
        candidates.append(
            {
                "rating": match.group("rating"),
                "context": re.sub(r"\s+", " ", text[start:end]).strip(),
            }
        )
        if len(candidates) >= 15:
            break

    counts = []
    for match in COUNT_RE.finditer(text):
        counts.append({"count": match.group("count"), "context": line_context(text, match.start())})
        if len(counts) >= 15:
            break

    structured: list[dict[str, Any]] = []
    for block in jsonld_blocks(html):
        for item in flatten_jsonld(block):
            aggregate = item.get("aggregateRating") if isinstance(item, dict) else None
            if isinstance(aggregate, dict):
                structured.append(
                    {
                        "name": item.get("name"),
                        "ratingValue": aggregate.get("ratingValue"),
                        "reviewCount": aggregate.get("reviewCount") or aggregate.get("ratingCount"),
                        "bestRating": aggregate.get("bestRating"),
                    }
                )

    return {
        "structured_ratings": structured,
        "rating_text_candidates": candidates,
        "review_count_candidates": counts,
        "review_snippets": extract_review_snippets(text),
    }


def flatten_jsonld(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        out = [value]
        graph = value.get("@graph")
        if isinstance(graph, list):
            for child in graph:
                out.extend(flatten_jsonld(child))
        return out
    if isinstance(value, list):
        out: list[dict[str, Any]] = []
        for child in value:
            out.extend(flatten_jsonld(child))
        return out
    return []


def line_context(text: str, pos: int) -> str:
    start = text.rfind("\n", 0, pos)
    end = text.find("\n", pos)
    if start == -1:
        start = 0
    if end == -1:
        end = len(text)
    return text[start:end].strip()


def extract_review_snippets(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    snippets: list[str] = []
    for index, line in enumerate(lines):
        lower = line.lower()
        has_review_signal = (
            DATE_RE.search(line)
            or "stars" in lower
            or "rated" in lower
            or "review" in lower
        )
        if not has_review_signal:
            continue
        window = " ".join(lines[max(0, index - 2) : min(len(lines), index + 5)])
        window = re.sub(r"\s+", " ", window).strip()
        if len(window) < 45 or window in snippets:
            continue
        snippets.append(window[:900])
        if len(snippets) >= 30:
            break
    return snippets


def click_review_surfaces(page: Any) -> None:
    labels = [
        "Reviews",
        "Google reviews",
        "Yelp reviews",
        "See all reviews",
        "Read reviews",
        "More reviews",
        "Customer reviews",
        "View all",
    ]
    for label in labels:
        locator = page.get_by_text(label, exact=False).first
        try:
            if locator.count() and locator.is_visible(timeout=1200):
                locator.click(timeout=2000)
                page.wait_for_timeout(2500)
        except Exception:
            continue


def scroll_for_reviews(page: Any, passes: int) -> None:
    for _ in range(passes):
        try:
            page.mouse.wheel(0, 2200)
        except Exception:
            pass
        page.wait_for_timeout(1400)
        try:
            page.keyboard.press("PageDown")
        except Exception:
            pass
        page.wait_for_timeout(900)


def close_known_modals(page: Any) -> None:
    """Dismiss platform "store is closed" dialogs that would otherwise sit on
    top of the page and intercept clicks meant for review surfaces below.
    Grubhub blocks with a real modal ("Schedule my order") when the
    restaurant is outside business hours, closed via a back-arrow button
    (testid below, not an X) - confirmed live against Camino Real Wyandotte
    while it was actually closed. Uber Eats/DoorDash instead show a
    non-blocking inline banner, so there's nothing to dismiss for those."""
    try:
        page.locator('[data-testid="close-cart-edit-modal"]').first.click(timeout=2000)
    except Exception:
        pass


def save_page(page: Any, source: str, url: str, out_dir: Path, scroll_passes: int) -> SavedPage:
    page.goto(url, wait_until="domcontentloaded", timeout=80000)
    page.wait_for_timeout(5000)
    close_known_modals(page)
    click_review_surfaces(page)
    scroll_for_reviews(page, scroll_passes)
    click_review_surfaces(page)
    scroll_for_reviews(page, max(2, scroll_passes // 2))
    html = page.content()
    text = clean_text(html)
    final_url = page.url
    digest = hashlib.sha1(final_url.encode()).hexdigest()[:10]
    stem = f"{slug(source)}-{slug(urlparse(final_url).path or urlparse(final_url).netloc)}-{digest}"
    html_path = out_dir / f"{stem}.html"
    text_path = out_dir / f"{stem}.txt"
    screenshot_path = out_dir / f"{stem}.png"
    html_rel: str | None = None
    if len(html.encode("utf-8")) <= 8_000_000:
        html_path.write_text(html, encoding="utf-8")
        html_rel = str(html_path.relative_to(ROOT))
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
        extracted=extract_rating_candidates(text, html),
    )


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


def discover_urls(page: Any) -> dict[str, list[str]]:
    candidates: dict[str, list[str]] = {key: list(value) for key, value in DIRECT_URLS.items()}
    for source, query in DIRECT_SOURCE_SEARCHES.items():
        try:
            links = google_search_links(page, query)
        except Exception as exc:
            candidates.setdefault("_errors", []).append(f"{source} discovery: {type(exc).__name__}: {exc}")
            continue
        if source == "google_search":
            candidates.setdefault(source, []).append(f"https://www.google.com/search?q={quote_plus(query)}")
            continue
        for link in links:
            detected = source_for_url(link, source)
            if detected != source and source != "postmates_uber_eats":
                continue
            if source == "postmates_uber_eats" and detected != "postmates_uber_eats":
                continue
            candidates.setdefault(source, [])
            if link not in candidates[source]:
                candidates[source].append(link)
        time.sleep(1)
    return candidates


def combine_review_text(saved_pages: list[SavedPage], out_dir: Path) -> Path:
    combined = out_dir / "camino-real-wyandotte-raw-review-and-rating-text.txt"
    chunks = [
        "# Camino Real Mexican Grill Wyandotte Raw Review and Rating Text",
        "",
        f"Target: {TARGET['name']}",
        f"Address: {TARGET['address']}",
        f"Collected at local date: {time.strftime('%Y-%m-%d')}",
        "",
    ]
    for saved in saved_pages:
        text = (ROOT / saved.text_path).read_text(encoding="utf-8", errors="replace")
        chunks.extend(
            [
                "",
                "============================================================",
                f"Source: {saved.source}",
                f"URL: {saved.final_url}",
                f"Title: {saved.title}",
                "Extracted signals:",
                json.dumps(saved.extracted, ensure_ascii=False, indent=2),
                "============================================================",
                "",
                text,
            ]
        )
    combined.write_text("\n".join(chunks), encoding="utf-8")
    return combined


def summarize(saved_pages: list[SavedPage]) -> dict[str, Any]:
    source_summary: dict[str, Any] = {}
    for saved in saved_pages:
        entry = source_summary.setdefault(
            saved.source,
            {
                "pages": [],
                "best_structured_ratings": [],
                "rating_text_candidates": [],
                "review_count_candidates": [],
                "review_snippet_count": 0,
            },
        )
        entry["pages"].append(
            {
                "url": saved.final_url,
                "title": saved.title,
                "text_path": saved.text_path,
                "screenshot_path": saved.screenshot_path,
            }
        )
        entry["best_structured_ratings"].extend(saved.extracted.get("structured_ratings", []))
        entry["rating_text_candidates"].extend(saved.extracted.get("rating_text_candidates", [])[:5])
        entry["review_count_candidates"].extend(saved.extracted.get("review_count_candidates", [])[:5])
        entry["review_snippet_count"] += len(saved.extracted.get("review_snippets", []))
    return source_summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--latitude", type=float, default=DEFAULT_LOCATION["latitude"])
    parser.add_argument("--longitude", type=float, default=DEFAULT_LOCATION["longitude"])
    parser.add_argument("--headful", action="store_true")
    parser.add_argument("--per-source-limit", type=int, default=4)
    parser.add_argument("--scroll-passes", type=int, default=8)
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    saved_pages: list[SavedPage] = []
    notes: dict[str, Any] = {
        "target": TARGET,
        "geolocation": {"latitude": args.latitude, "longitude": args.longitude},
        "discovered_urls": {},
        "saved_pages": [],
        "source_summary": {},
        "errors": [],
    }

    with Camoufox(headless=not args.headful, humanize=True) as browser:
        context = browser.new_context(
            viewport={"width": 1365, "height": 900},
            locale="en-US",
            timezone_id="America/Detroit",
            geolocation={"latitude": args.latitude, "longitude": args.longitude},
            permissions=["geolocation"],
        )
        page = context.new_page()
        print("Discovering review source URLs through Google", flush=True)
        candidates = discover_urls(page)
        notes["discovered_urls"] = candidates
        for source, urls in candidates.items():
            if source.startswith("_"):
                notes["errors"].extend(urls)
                continue
            for url in urls[: args.per_source_limit]:
                try:
                    print(f"Saving {source}: {url}", flush=True)
                    saved_pages.append(save_page(page, source, url, args.output, args.scroll_passes))
                except Exception as exc:
                    notes["errors"].append(f"{source} {url}: {type(exc).__name__}: {exc}")
        context.close()

    notes["saved_pages"] = [asdict(saved) for saved in saved_pages]
    notes["source_summary"] = summarize(saved_pages)
    combined = combine_review_text(saved_pages, args.output)
    notes["combined_text_path"] = str(combined.relative_to(ROOT))
    notes_path = args.output / "spike-review-notes.json"
    notes_path.write_text(json.dumps(notes, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {combined.relative_to(ROOT)}", flush=True)
    print(f"Wrote {notes_path.relative_to(ROOT)}", flush=True)


if __name__ == "__main__":
    main()
