#!/usr/bin/env python3
"""Spike DoorDash menu discovery/snapshot parser for Downriver restaurants."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

from bs4 import BeautifulSoup
from camoufox.sync_api import Camoufox


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "external-data/derived/downriver-mexican-restaurants-reviewed.jsonl"
DEFAULT_OUTPUT = ROOT / "external-data/menu-scraping/doordash_spike"
DEFAULT_LOCATION = {
    "latitude": 42.197513,
    "longitude": -83.269677,
}

PRICE_KEYS = {"price", "displayPrice", "unitAmount", "basePrice", "finalPrice"}
NAME_KEYS = {"name", "title", "displayName"}
DESC_KEYS = {"description", "itemDescription", "subtitle"}
STOPWORDS = {
    "a",
    "an",
    "and",
    "bar",
    "grill",
    "mexican",
    "of",
    "restaurant",
    "taqueria",
    "the",
}


@dataclass
class Restaurant:
    record: dict[str, Any]
    name: str
    city: str
    address: str


def load_restaurants(path: Path, limit: int) -> list[Restaurant]:
    restaurants: list[Restaurant] = []
    with path.open() as f:
        for line in f:
            if not line.strip():
                continue
            record = json.loads(line)
            tags = record.get("tags", {})
            name = tags.get("name") or tags.get("official_name") or ""
            if not name:
                continue
            city = tags.get("addr:city", "")
            address = " ".join(
                part
                for part in [
                    tags.get("addr:housenumber", ""),
                    tags.get("addr:street", ""),
                    city,
                    tags.get("addr:state", "MI"),
                ]
                if part
            )
            restaurants.append(Restaurant(record=record, name=name, city=city, address=address))
            if len(restaurants) >= limit:
                break
    return restaurants


def slug(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return cleaned[:80] or "restaurant"


def unwrap_google_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.path == "/url":
        qs = parse_qs(parsed.query)
        if qs.get("q"):
            return qs["q"][0]
    return url


def google_candidates(page: Any, restaurant: Restaurant) -> list[str]:
    query_bits = [restaurant.name]
    if restaurant.city:
        query_bits.append(restaurant.city)
    query_bits.append("MI DoorDash")
    query = " ".join(query_bits)
    url = f"https://www.google.com/search?q={quote_plus('site:doordash.com/store ' + query)}"
    page.goto(url, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(2500)
    links = page.locator("a").evaluate_all(
        """els => els.map(a => a.href).filter(Boolean)"""
    )
    candidates: list[str] = []
    for link in links:
        target = unquote(unwrap_google_url(link))
        if "doordash.com/store" in target and target not in candidates:
            candidates.append(target)
    return candidates


def doordash_search_candidates(page: Any, restaurant: Restaurant) -> list[str]:
    query = " ".join(part for part in [restaurant.name, restaurant.city, "MI"] if part)
    url = f"https://www.doordash.com/search/store/{quote_plus(query)}/"
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(5000)
    links = page.locator("a").evaluate_all(
        """els => els.map(a => a.href).filter(Boolean)"""
    )
    candidates: list[str] = []
    for link in links:
        target = unquote(link)
        if "doordash.com/store" in target and target not in candidates:
            candidates.append(target)
    return candidates


def recursively_find_items(value: Any, path: str = "") -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        keys = set(value)
        has_name = bool(keys & NAME_KEYS)
        has_desc = bool(keys & DESC_KEYS)
        has_price = bool(keys & PRICE_KEYS)
        if has_name and (has_desc or has_price):
            name = first_string(value, NAME_KEYS)
            if name and not looks_like_container(name):
                found.append(
                    {
                        "name": name,
                        "description": first_string(value, DESC_KEYS),
                        "price": first_present(value, PRICE_KEYS),
                        "source_path": path,
                    }
                )
        for key, child in value.items():
            found.extend(recursively_find_items(child, f"{path}.{key}" if path else str(key)))
    elif isinstance(value, list):
        for i, child in enumerate(value):
            found.extend(recursively_find_items(child, f"{path}[{i}]"))
    return found


def first_string(value: dict[str, Any], keys: set[str]) -> str:
    for key in keys:
        item = value.get(key)
        if isinstance(item, str) and item.strip():
            return item.strip()
    return ""


def first_present(value: dict[str, Any], keys: set[str]) -> Any:
    for key in keys:
        item = value.get(key)
        if item not in (None, ""):
            return item
    return None


def looks_like_container(name: str) -> bool:
    lowered = name.strip().lower()
    return lowered in {
        "menu",
        "doordash",
        "popular items",
        "reviews",
        "featured items",
        "restaurant info",
    }


def dedupe_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for item in items:
        key = (
            item.get("name") or "",
            item.get("description") or "",
            json.dumps(item.get("price"), sort_keys=True, default=str),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def parse_snapshot(html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    meta_description = ""
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        meta_description = str(meta["content"])

    parsed_json: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    for script in soup.find_all("script"):
        raw = script.string or script.get_text()
        raw = raw.strip()
        if not raw:
            continue
        if script.get("type") == "application/ld+json" or raw.startswith("{") or raw.startswith("["):
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            parsed_json.append(data if isinstance(data, dict) else {"value": data})
            items.extend(recursively_find_items(data))

    headings = [h.get_text(" ", strip=True) for h in soup.select("h1,h2,h3") if h.get_text(strip=True)]
    return {
        "title": title,
        "meta_description": meta_description,
        "headings": headings[:60],
        "items": dedupe_items(items),
        "json_script_count": len(parsed_json),
    }


def close_known_modals(page: Any) -> None:
    """Defensive dismissal in case a store shows a blocking "closed" dialog.
    Confirmed DoorDash itself shows a non-blocking inline banner instead
    (a store page loaded fully with no modal while genuinely closed), but
    this script also lands on whatever Google/DoorDash search turns up for
    an arbitrary restaurant, so this is cheap insurance rather than a
    confirmed-necessary fix like the Grubhub one in the other spike
    scripts."""
    try:
        page.locator('[data-testid="close-cart-edit-modal"]').first.click(timeout=1500)
    except Exception:
        pass


def snapshot_page(page: Any, url: str, out_dir: Path, restaurant_slug: str) -> dict[str, Any]:
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(8000)
    close_known_modals(page)
    page.mouse.wheel(0, 2400)
    page.wait_for_timeout(2500)
    html = page.content()
    digest = hashlib.sha1(url.encode()).hexdigest()[:10]
    stem = f"{restaurant_slug}-{digest}"
    html_path = out_dir / f"{stem}.html"
    png_path = out_dir / f"{stem}.png"
    html_path.write_text(html, encoding="utf-8")
    page.screenshot(path=str(png_path), full_page=True)
    parsed = parse_snapshot(html)
    parsed.update({"url": url, "html_path": str(html_path.relative_to(ROOT)), "screenshot_path": str(png_path.relative_to(ROOT))})
    return parsed


def tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 2 and token not in STOPWORDS
    }


def snapshot_matches(restaurant: Restaurant, snapshot: dict[str, Any]) -> tuple[bool, str]:
    haystack = " ".join(
        [
            snapshot.get("title", ""),
            snapshot.get("meta_description", ""),
            " ".join(snapshot.get("headings", [])[:5]),
        ]
    ).lower()
    name_tokens = tokens(restaurant.name)
    overlap = name_tokens & tokens(haystack)
    city_match = bool(restaurant.city and restaurant.city.lower() in haystack)
    if city_match and overlap:
        return True, f"city match plus token overlap: {sorted(overlap)}"
    if len(name_tokens) >= 2 and len(overlap) >= 2:
        return True, f"name token overlap: {sorted(overlap)}"
    return False, f"rejected; city_match={city_match}, token_overlap={sorted(overlap)}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--candidate-limit", type=int, default=4)
    parser.add_argument("--latitude", type=float, default=DEFAULT_LOCATION["latitude"])
    parser.add_argument("--longitude", type=float, default=DEFAULT_LOCATION["longitude"])
    parser.add_argument("--headful", action="store_true")
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    restaurants = load_restaurants(args.input, args.limit)
    results: list[dict[str, Any]] = []

    with Camoufox(headless=not args.headful, humanize=True) as browser:
        for restaurant in restaurants:
            context = browser.new_context(
                viewport={"width": 1365, "height": 900},
                locale="en-US",
                timezone_id="America/Detroit",
                geolocation={"latitude": args.latitude, "longitude": args.longitude},
                permissions=["geolocation"],
            )
            page = context.new_page()
            print(f"Searching {restaurant.name} {restaurant.city}".strip(), flush=True)
            errors: list[str] = []
            try:
                candidate_urls = google_candidates(page, restaurant)
            except Exception as exc:
                errors.append(f"google_search: {type(exc).__name__}: {exc}")
                candidate_urls = []
            if not candidate_urls:
                try:
                    candidate_urls = doordash_search_candidates(page, restaurant)
                except Exception as exc:
                    errors.append(f"doordash_search: {type(exc).__name__}: {exc}")
            result = {
                "restaurant": restaurant.record,
                "query_name": restaurant.name,
                "query_city": restaurant.city,
                "candidates": candidate_urls,
                "errors": errors,
                "snapshot": None,
                "candidate_checks": [],
            }
            for candidate_url in candidate_urls[: args.candidate_limit]:
                print(f"  Checking {candidate_url}", flush=True)
                snapshot = snapshot_page(page, candidate_url, args.output, slug(restaurant.name))
                is_match, reason = snapshot_matches(restaurant, snapshot)
                result["candidate_checks"].append(
                    {
                        "url": candidate_url,
                        "title": snapshot.get("title"),
                        "reason": reason,
                        "matched": is_match,
                    }
                )
                if is_match:
                    result["snapshot"] = snapshot
                    print(f"  Accepted: {reason}", flush=True)
                    break
                print(f"  {reason}", flush=True)
            if result["snapshot"]:
                results.append(result)
                context.close()
                break
            results.append(result)
            context.close()
            time.sleep(1)

    output_json = args.output / "results.json"
    output_json.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {output_json.relative_to(ROOT)}", flush=True)


if __name__ == "__main__":
    main()
