#!/usr/bin/env python3
"""Parse DoorDash JSON-LD captured from the Camofox REST browser.

DoorDash's JSON-LD Menu script is missing whole categories on at least one
sampled restaurant (Sides, Desserts, Beverages, Breakfast were absent even
though they're visible on the rendered page), and it rolls the top items up
into a "Most Ordered" section that duplicates items already listed under
their real category. To fix both problems, pass --ratings pointing at a DOM
extraction (one entry per store item, matched by name) that supplies:

- like_percent / like_review_count for items with a visible rating
- featured_rank for the (usually 3) items carrying a "#N Most liked" badge
- section, used only as a fallback category for items whose *only* JSON-LD
  appearance is inside "Most Ordered" (no other section lists them), and for
  items missing from the JSON-LD entirely

Items are placed under their real (non-"Most Ordered") JSON-LD category
whenever one exists; "Most Ordered" itself is never emitted as an output
section. Anything found only in "Most Ordered" JSON-LD, or only in the DOM,
gets "special": "featured item" and is filed under its DOM-reported section.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

MOST_ORDERED = "Most Ordered"


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


def collect_occurrences(menu: dict[str, Any]) -> tuple[dict[str, list[tuple[str, dict[str, Any]]]], list[str]]:
    """Map each item title to every (section name, raw item) it appears under, and record section order."""
    occurrences: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    section_order: list[str] = []
    for section in flatten_sections(menu.get("hasMenuSection", [])):
        section_name = section.get("name") or ""
        if section_name not in section_order:
            section_order.append(section_name)
        for item in flatten_sections(section.get("hasMenuItem", [])):
            name = (item.get("name") or "").strip()
            if not name:
                continue
            # Some titles carry stray trailing whitespace in the JSON-LD (e.g.
            # "Camino Real Skillet "); normalize so DOM-name matching works.
            occurrences.setdefault(name, []).append((section_name, item))
    return occurrences, section_order


def build_item(name: str, description: str, price: str | None, rating: dict[str, Any] | None, featured: bool) -> dict[str, Any]:
    parsed_item: dict[str, Any] = {
        "title": name,
        "ingredients_or_description": description,
        "price": price,
    }
    if featured:
        parsed_item["special"] = "featured item"
    if rating is not None:
        if rating.get("featured_rank") is not None:
            parsed_item["featured_rank"] = rating["featured_rank"]
        if rating.get("like_percent") is not None:
            parsed_item["like_percent"] = rating["like_percent"]
            parsed_item["like_review_count"] = rating["like_review_count"]
    return parsed_item


def parse_menu(menu: dict[str, Any], ratings_by_name: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    occurrences, section_order = collect_occurrences(menu)
    sections: dict[str, list[dict[str, Any]]] = {}
    output_order: list[str] = []

    def add_item(section_name: str, item: dict[str, Any]) -> None:
        if section_name not in sections:
            sections[section_name] = []
            output_order.append(section_name)
        sections[section_name].append(item)

    for title, occ in occurrences.items():
        non_rollup = [o for o in occ if o[0] != MOST_ORDERED]
        is_featured = len(non_rollup) < len(occ)  # appears under "Most Ordered" at least once
        # Prefer the longest description across all occurrences; JSON-LD sometimes
        # repeats the item with a thinner description in one section vs. another.
        description = max((o[1].get("description") or "" for o in occ), key=len)
        rating = ratings_by_name.get(title)
        if non_rollup:
            section_name, item = non_rollup[0]
        else:
            # Only ever listed under "Most Ordered" (e.g. Arroz, Horchata) - JSON-LD
            # doesn't say its real category since that category is entirely missing;
            # fall back to what the DOM reports.
            section_name = (rating or {}).get("section") or MOST_ORDERED
            item = occ[0][1]
        price = parse_price(item)
        add_item(section_name, build_item(title, description, price, rating, is_featured))

    known_titles = set(occurrences.keys())
    for name, rating in ratings_by_name.items():
        if name in known_titles:
            continue
        # True DOM-only item: JSON-LD never mentions it at all (e.g. whole
        # missing categories like Sides/Desserts/Beverages/Breakfast).
        section_name = rating.get("section") or "Uncategorized"
        price = rating.get("price")
        add_item(
            section_name,
            build_item(
                name,
                rating.get("description") or "",
                f"${price}" if price is not None else None,
                rating,
                featured=rating.get("featured_rank") is not None,
            ),
        )

    # Emit known JSON-LD sections (minus "Most Ordered") in their original order first,
    # then any DOM-only/fallback sections in whatever order they were first encountered.
    ordered_names = [s for s in section_order if s != MOST_ORDERED and s in sections]
    ordered_names += [s for s in output_order if s not in ordered_names]
    return [{"section": name, "items": sections[name]} for name in ordered_names]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--ratings",
        type=Path,
        default=None,
        help=(
            "All-item-card DOM extraction, one entry per store item with "
            "name/description/price/section/like_percent/like_review_count/featured_rank "
            "(camofox eval wrapper: {result: [...]})"
        ),
    )
    args = parser.parse_args()

    response = json.loads(args.input.read_text())
    scripts = response.get("result") or []
    parsed_scripts = [json.loads(script) for script in scripts]
    restaurant = next((s for s in parsed_scripts if s.get("@type") == "Restaurant"), {})
    menu = next((s for s in parsed_scripts if s.get("@type") == "Menu"), {})
    faq = next((s for s in parsed_scripts if s.get("@type") == "FAQPage"), {})

    ratings_by_name: dict[str, dict[str, Any]] = {}
    if args.ratings is not None:
        ratings_response = json.loads(args.ratings.read_text())
        for entry in ratings_response.get("result") or []:
            name = (entry.get("name") or "").strip()
            if name:
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
    featured_count = sum(
        1 for section in output["menu_sections"] for item in section["items"] if item.get("special") == "featured item"
    )
    rated_count = sum(
        1 for section in output["menu_sections"] for item in section["items"] if item.get("like_percent") is not None
    )
    print(
        f"Wrote {args.output} ({section_count} sections, {item_count} items, "
        f"{featured_count} featured, {rated_count} with a like rating)"
    )


if __name__ == "__main__":
    main()
