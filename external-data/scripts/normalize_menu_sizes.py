#!/usr/bin/env python3
"""Normalize size-per-item menus into one item with a Size option.

Merchants model size in at least three ways on the same platform (see
external-data/menu-scraping/doordash-menu-scraping-notes.md):

  1. One item + a `Sizes` group, each size carrying its own modifier groups
     priced for that size.                                   (Hungry Howie's)
  2. Size baked into separate top-level items - "Small Thin Crust",
     "Large Thin Crust" as distinct menu entries.            (Jet's Pizza)
  3. A per-item variant group named "Choose an option - <Item>" whose options
     are really size/crust variants.                         (Jet's specialty)

Cross-restaurant display needs one shape. This converts 2 and 3 into 1, so
every multi-size item ends up as a single item with a `Size` group - which is
what shape 1 already is natively, and therefore lossless to merge into.

Storage: shape 2 duplicates the full modifier tree once per size. Measured on
Jet's "Build Your Own" section - 13 items, 29,330 bytes of option data where
~2,433 would do, i.e. 12x. Where every size shares an identical modifier
structure this script hoists it to the item level and stores it once; where
sizes genuinely differ it nests per size (shape 1) rather than dropping detail.

Merging is deliberately conservative - a wrong merge silently fuses two real
menu items, which is worse than leaving a menu un-normalized:

  - Only items in the same section merge.
  - Titles must reduce to an identical residual after stripping exactly one
    size token from the front or back (SIZE_TOKENS).
  - A group of one is left alone.

Near-misses (same residual but blocked by a rule) are reported so the rules can
be tightened against real menus rather than guessed at.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

_spec = importlib.util.spec_from_file_location(
    "parse_doordash_itempage", Path(__file__).resolve().parent / "parse_doordash_itempage.py"
)
_dd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_dd)

# Ordered so display order is menu order, not alphabetical. Longest-first
# matching happens in strip_size_token, so "X-Large" wins over "Large".
SIZE_TOKENS: list[str] = [
    "Junior", "Jr", "Personal", "Mini", "Kids",
    "Small", "Sm", "Medium", "Med", "Regular",
    "Large", "Lg", "X-Large", "XLarge", "Extra Large", "XL",
    "Jumbo", "Family", "Party Tray",
]
SIZE_ORDER = {name.lower(): i for i, name in enumerate(SIZE_TOKENS)}
INCH_RE = re.compile(r'^(\d{1,2})\s*(?:"|-?inch\b)', re.I)

VARIANT_GROUP_RE = re.compile(r"^choose an option\s*[-–]\s*", re.I)
SIZE_GROUP_NAMES = {"size", "sizes"}

# Menu codes ("C17.", "S6.", "33.") prefix 103 of 143 titles on a sampled
# Chinese restaurant. They belong in their own field, not in the display title:
# nobody searches "C17", and the codes differ between two sizes of the same
# dish, which would block a legitimate size merge.
#
# Two alternations, because the delimiter rules differ and the numeric case is
# genuinely dangerous:
#   - Letter-prefixed ("S8.Seafood Delight") - trailing space optional, since
#     real menus omit it.
#   - Pure numeric ("18. Vegetable Fried Rice") - trailing space REQUIRED, so a
#     decimal price-style title like "1.50 TACO (TUESDAY)" is not mistaken for
#     code "1" followed by "50 TACO".
# Verified against 375 real titles across four restaurants: 103 matched, and
# every digit-leading non-code survived intact ("2 oz Guacamole", "4 Corner
# Pizza®", "8” Chocolate Chip Cookie", "3-Topping", "20 oz Dasani Water").
# Third alternation added after finding "NO.6. Pepper Steak & Almond Chicken"
# (10 items on one store): a word prefix separated from its number by its own
# period, which the letters-immediately-followed-by-digits rule missed. Kept
# tight to the literal "NO" spelling rather than any word, so a dish genuinely
# starting with a short word and a number is not eaten.
MENU_CODE_RE = re.compile(
    r"^(?:"
    r"(NO\.?\s*\d{1,3}[a-z]?)[.)]\s*"       # NO.6. / NO 6)
    r"|([A-Za-z]{1,2}\d{1,3}[a-z]?)[.)]\s*"  # C17. / S8.Seafood
    r"|(\d{1,3})[.)]\s+"                     # 18. (space required - see above)
    r")",
    re.I,
)


def extract_menu_code(item: dict[str, Any]) -> bool:
    """Move a leading menu code out of the title into `menu_code`."""
    # Scraped titles carry stray leading/trailing whitespace (6 items on one
    # store), which would otherwise defeat the anchored ^ match.
    if item.get("title"):
        item["title"] = item["title"].strip()
    match = MENU_CODE_RE.match(item.get("title") or "")
    if not match:
        return False
    residual = item["title"][match.end():].strip()
    if not residual:
        return False
    item["menu_code"] = match.group(1) or match.group(2) or match.group(3)
    # `original_title` may already hold the exact DoorDash string when display
    # normalization changed Unicode punctuation before the code was removed.
    item.setdefault("original_title", item["title"])
    item["title"] = residual
    return True


def normalize_display_title(item: dict[str, Any]) -> bool:
    """Normalize compatibility-width title glyphs without altering source text.

    Some DoorDash merchants use full-width CJK punctuation in otherwise Latin
    menu titles, for example ``Egg Foo Young（4pc）`` and ``Soup (32 quart）``.
    NFKC makes those titles compare and search consistently (``(4pc)``), while
    preserving actual Han/Kana/Hangul characters.  Keep the untouched scraped
    value in ``original_title`` for traceability.
    """
    title = item.get("title")
    if not title:
        return False
    normalized = unicodedata.normalize("NFKC", title).strip()
    if normalized == title:
        return False
    item.setdefault("original_title", title)
    item["title"] = normalized
    return True


def strip_size_token(title: str) -> tuple[str | None, str]:
    """Returns (size, residual). Size is None when no token is found."""
    text = title.strip()
    inch = INCH_RE.match(text)
    if inch:
        return f'{inch.group(1)}"', text[inch.end():].strip(" -–")

    for token in sorted(SIZE_TOKENS, key=len, reverse=True):
        pattern = re.compile(rf"^{re.escape(token)}\b[\s-]*", re.I)
        match = pattern.match(text)
        if match:
            residual = text[match.end():].strip()
            if residual:
                return token, residual
        pattern_tail = re.compile(rf"[\s(-]*\b{re.escape(token)}\)?$", re.I)
        match = pattern_tail.search(text)
        if match and text[: match.start()].strip():
            return token, text[: match.start()].strip()
    return None, text


def size_sort_key(size: str) -> tuple[int, float, str]:
    inch = re.match(r'^(\d+)"$', size)
    if inch:
        return (0, float(inch.group(1)), size)
    return (1, SIZE_ORDER.get(size.lower(), 99), size)


def structure_signature(item: dict[str, Any]) -> str:
    """Modifier structure ignoring prices - two sizes with the same groups and
    option names but different prices share a signature."""
    return json.dumps(
        [[g["group"], [o["name"] for o in g["options"]]] for g in item.get("options") or []],
        sort_keys=True,
    )


def rename_variant_groups(item: dict[str, Any]) -> bool:
    """Shape 3: "Choose an option - Super Special" is a size/crust picker in all
    but name. Renamed to `Size` so cross-restaurant consumers find it where they
    find every other size picker."""
    renamed = False
    for group in item.get("options") or []:
        if VARIANT_GROUP_RE.match(group["group"] or ""):
            group["group"] = "Size"
            renamed = True
    return renamed


def merge_group(items: list[dict[str, Any]], residual: str, sizes: list[str]) -> dict[str, Any]:
    """Fold sibling size-items into one item carrying a synthesized Size group."""
    paired = sorted(zip(sizes, items), key=lambda p: size_sort_key(p[0]))
    signatures = {structure_signature(i) for _, i in paired}
    shared = len(signatures) == 1

    base_prices = [i.get("price_min") or 0.0 for _, i in paired]
    floor = min(base_prices)

    size_options = []
    for size, item in paired:
        entry: dict[str, Any] = {
            "name": size,
            "price": round((item.get("price_min") or 0.0) - floor, 2),
            "description": "",
            "absolute_price": item.get("price_min"),
        }
        if not shared:
            # Sizes differ structurally - keep each size's own groups nested,
            # which is exactly shape 1 and loses nothing.
            entry["nested"] = item.get("options") or []
        size_options.append(entry)

    merged: dict[str, Any] = {
        "title": residual,
        "ingredients_or_description": next(
            (i.get("ingredients_or_description") or "" for _, i in paired if i.get("ingredients_or_description")),
            "",
        ),
        "price": f"${floor:.2f}",
        "price_min": floor,
        "price_max": max(i.get("price_max") or 0.0 for _, i in paired),
        "options": [
            {
                "group": "Size",
                "required": True,
                "min_select": 1,
                "max_select": 1,
                "free_count": 0,
                "selection": "single_select",
                "options": size_options,
            }
        ],
        "size_normalized": True,
        "merged_from": [i["title"] for _, i in paired],
    }
    source_item_ids = list(dict.fromkeys(
        str(item["source_item_id"])
        for _, item in paired
        if item.get("source_item_id") is not None
    ))
    if source_item_ids:
        # A normalized size family no longer has one DoorDash item ID, but its
        # source lineage must remain inspectable.
        merged["source_item_ids"] = source_item_ids
    section_memberships = list(dict.fromkeys(
        section
        for _, item in paired
        for section in (item.get("section_memberships") or [])
        if isinstance(section, str) and section
    ))
    if section_memberships:
        merged["section_memberships"] = section_memberships
    if shared:
        # Every size had the same structure - store the modifier groups once.
        merged["options"].extend(paired[0][1].get("options") or [])

    merged["option_index"] = _dd.build_option_index(merged["options"])
    badges = _dd.build_dietary_badges(
        merged["option_index"], f"{merged['title']} {merged['ingredients_or_description']}"
    )
    if badges:
        merged["dietary_badges"] = badges
    cross = [c for _, i in paired for c in (i.get("cross_sell") or [])]
    if cross:
        seen, unique = set(), []
        for group in cross:
            if group["group"] not in seen:
                seen.add(group["group"])
                unique.append(group)
        merged["cross_sell"] = unique
    return merged


def normalize_section(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int, list[str]]:
    buckets: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    order: list[str] = []
    singles: list[dict[str, Any]] = []

    for item in items:
        size, residual = strip_size_token(item["title"])
        if size is None:
            singles.append(item)
            continue
        key = residual.lower()
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append((size, item))

    output: list[dict[str, Any]] = []
    merged_count = 0
    notes: list[str] = []
    consumed: set[int] = set()

    for key in order:
        members = buckets[key]
        if len(members) < 2:
            # A lone "Large Deep Dish" stays as-is; stripping its size would
            # rename the item for no benefit.
            output.append(members[0][1])
            continue
        residual = strip_size_token(members[0][1]["title"])[1]
        output.append(merge_group([i for _, i in members], residual, [s for s, _ in members]))
        merged_count += len(members) - 1
        notes.append(f"merged {len(members)} -> {residual!r}: {[i['title'] for _, i in members]}")
        consumed.update(id(i) for _, i in members)

    # Near-misses: residuals close enough that a human would call them the same
    # product, but not identical so the conservative rule declined to merge.
    # Confirmed real: Maria's "Large Side of Rice, Beans, or Papas" vs "Small
    # Side of Rice, Beans, or Papas (8oz)" - blocked by a trailing "(8oz)".
    # Reported rather than merged, so the rules get tightened against real
    # menus instead of guessed at.
    lone = [key for key in order if len(buckets[key]) == 1]
    for i, a in enumerate(lone):
        for b in lone[i + 1:]:
            if SequenceMatcher(None, a, b).ratio() >= 0.80:
                notes.append(
                    f"NEAR-MISS not merged (residuals {a!r} vs {b!r}): "
                    f"{buckets[a][0][1]['title']!r} / {buckets[b][0][1]['title']!r}"
                )

    output.extend(singles)
    return output, merged_count, notes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", type=Path, help="parsed menu JSON (parse_doordash_itempage.py output)")
    parser.add_argument("output", type=Path)
    parser.add_argument("--verbose", action="store_true", help="print every merge")
    args = parser.parse_args()

    doc = json.loads(args.input.read_text())
    total_merged = 0
    total_renamed = 0
    total_codes = 0
    total_display_titles_normalized = 0
    all_notes: list[str] = []

    for section in doc.get("menu_sections") or []:
        for item in section["items"]:
            if normalize_display_title(item):
                total_display_titles_normalized += 1
            if rename_variant_groups(item):
                total_renamed += 1
            # Before bucketing: codes differ between sizes of one dish and
            # would otherwise block the merge.
            if extract_menu_code(item):
                total_codes += 1
        section["items"], merged, notes = normalize_section(section["items"])
        total_merged += merged
        all_notes.extend(f"[{section['section']}] {n}" for n in notes)

    doc.setdefault("source", {})["normalization"] = {
        "size_items_merged": total_merged,
        "variant_groups_renamed_to_size": total_renamed,
        "menu_codes_extracted": total_codes,
        "display_titles_unicode_normalized": total_display_titles_normalized,
    }
    args.output.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")

    if args.verbose:
        for note in all_notes:
            print("  " + note)
    remaining = sum(len(s["items"]) for s in doc["menu_sections"])
    print(
        f"Wrote {args.output} ({remaining} items after merging {total_merged} size duplicates; "
        f"{total_renamed} variant groups renamed to 'Size'; {total_codes} menu codes extracted; "
        f"{total_display_titles_normalized} display titles Unicode-normalized)"
    )


if __name__ == "__main__":
    main()
