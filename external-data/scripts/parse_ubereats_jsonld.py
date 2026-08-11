#!/usr/bin/env python3
"""Parse Uber Eats JSON-LD captured from the Camofox REST browser.

Uber Eats embeds the menu inside the Restaurant script's `hasMenu` field
(unlike DoorDash, which uses a separate `Menu` script). Two things aren't in
the JSON-LD at all and are captured separately via DOM extraction, then
merged in here by item name (see
external-data/menu-scraping/ubereats_spike/camino-real-wyandotte-ubereats-all-item-ratings.json
for an example of that DOM-extraction shape):

- A "Featured items" carousel Uber Eats renders client-side (~19 items on
  the sampled restaurant). Items in it get a "special": "featured item" tag,
  and the top 3 additionally carry a "#N most liked" rank badge.
- A thumbs-up rating ("87% (56)") shown on most item cards, featured or not.
  Low-order items can lack one entirely, so it's optional per item.
- A separate "Popular" text badge (own leaf `<div>`, sibling to the item's
  description) seen on a restaurant with no "Featured items" carousel at
  all. It's not just a fallback label for items missing a rating - on the
  sampled restaurant, 158 of 269 items had no rating, but only 10 were
  marked "Popular". On any single physical card, "Popular" and a rating are
  mutually exclusive (never both). But the same dish name can appear on more
  than one physical card if it's duplicated across JSON-LD sections, and
  different copies can carry different signals - e.g. "Half BBQ Chicken"
  showed up under both "From the Broiler" and "Senior Citizens", one copy
  rated and the other tagged "Popular", so after merging by name the output
  item legitimately has both "like_percent" and "popular": true set. It gets
  its own field rather than folding into "special", since a "Popular" badge
  and a carousel "special": "featured item" tag are independent concepts
  that could in principle both be true for the same item, even though that
  combination hasn't been observed yet.
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any


def flatten_sections(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        sections: list[dict[str, Any]] = []
        for item in value:
            sections.extend(flatten_sections(item))
        return sections
    return []


def parse_price(item: dict[str, Any]) -> str | None:
    offers = item.get("offers")
    if isinstance(offers, dict):
        price = offers.get("price")
        return str(price) if price is not None else None
    return None


def parse_menu(menu: dict[str, Any], ratings_by_name: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    parsed_sections: list[dict[str, Any]] = []
    for section in flatten_sections(menu.get("hasMenuSection", [])):
        # Skip the "Featured items" rollup section itself: it duplicates items
        # that already live under their real category (Tacos, Burritos, ...),
        # and its entries carry no description here, only a name.
        if section.get("name") == "Featured items":
            continue
        items = []
        for item in flatten_sections(section.get("hasMenuItem", [])):
            name = item.get("name")
            if not name:
                continue
            # Uber Eats' JSON-LD HTML-escapes text (e.g. "Chips &amp; Salsa"),
            # unlike the carousel DOM extraction, which is already decoded.
            name = html.unescape(name)
            parsed_item: dict[str, Any] = {
                "title": name,
                "ingredients_or_description": html.unescape(item.get("description") or ""),
                "price": parse_price(item),
            }
            rating = ratings_by_name.get(name)
            if rating is not None:
                if rating.get("in_featured_carousel"):
                    parsed_item["special"] = "featured item"
                    parsed_item["featured_rank"] = rating.get("featured_rank")
                if rating.get("like_percent") is not None:
                    parsed_item["like_percent"] = rating["like_percent"]
                    parsed_item["like_review_count"] = rating["like_review_count"]
                if rating.get("is_popular"):
                    parsed_item["popular"] = True
            items.append(parsed_item)
        parsed_sections.append({"section": html.unescape(section.get("name") or ""), "items": items})
    return parsed_sections


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="Raw JSON-LD response (camofox eval wrapper: {result: [...]})")
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--ratings",
        type=Path,
        default=None,
        help=(
            "All-item-card DOM extraction, one entry per store-item card including "
            "the featured carousel's duplicates (camofox eval wrapper: {result: [...]})"
        ),
    )
    args = parser.parse_args()

    response = json.loads(args.input.read_text())
    scripts = response.get("result") or []
    parsed_scripts = [json.loads(script) for script in scripts]
    restaurant = next((s for s in parsed_scripts if s.get("@type") == "Restaurant"), {})
    menu = restaurant.get("hasMenu") or {}
    faq = next((s for s in parsed_scripts if s.get("@type") == "FAQPage"), {})

    ratings_by_name: dict[str, dict[str, Any]] = {}
    if args.ratings is not None:
        ratings_response = json.loads(args.ratings.read_text())
        for entry in ratings_response.get("result") or []:
            name = entry.get("name")
            if not name:
                continue
            # The carousel re-renders 19 items that also appear in their real
            # category section, so the same name can show up twice in this
            # DOM dump. Prefer the carousel copy since it carries the rank badge.
            existing = ratings_by_name.get(name)
            if existing is None or (entry.get("in_featured_carousel") and not existing.get("in_featured_carousel")):
                ratings_by_name[name] = entry

    output = {
        "source": {
            "response_path": str(args.input),
            "ratings_path": str(args.ratings) if args.ratings is not None else "",
            "url": restaurant.get("url") or "",
        },
        "restaurant": {
            "name": restaurant.get("name") or "",
            "address": restaurant.get("address") or {},
            "telephone": restaurant.get("telephone") or "",
            "serves_cuisine": restaurant.get("servesCuisine") or [],
            "aggregate_rating": restaurant.get("aggregateRating") or {},
            "description": restaurant.get("description") or "",
        },
        "menu_sections": parse_menu(menu, ratings_by_name),
        "faq": faq.get("mainEntity") or [],
    }
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    section_count = len(output["menu_sections"])
    item_count = sum(len(section["items"]) for section in output["menu_sections"])
    featured_matched = sum(
        1
        for section in output["menu_sections"]
        for item in section["items"]
        if item.get("special") == "featured item"
    )
    rated_matched = sum(
        1 for section in output["menu_sections"] for item in section["items"] if item.get("like_percent") is not None
    )
    popular_matched = sum(
        1 for section in output["menu_sections"] for item in section["items"] if item.get("popular")
    )
    featured_total = sum(1 for r in ratings_by_name.values() if r.get("in_featured_carousel"))
    print(
        f"Wrote {args.output} ({section_count} sections, {item_count} items, "
        f"{featured_matched}/{featured_total} featured items matched, "
        f"{rated_matched}/{item_count} items have a like rating, "
        f"{popular_matched} popular)"
    )


if __name__ == "__main__":
    main()
