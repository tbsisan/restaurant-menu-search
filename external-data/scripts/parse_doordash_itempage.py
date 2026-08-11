#!/usr/bin/env python3
"""Turn a spike_doordash_network_capture.py harvest into project-standard menu JSON.

Input is the `harvest` output (one entry per item, each holding the raw
`data.itemPage` payload from DoorDash's /graphql/itemPage endpoint); a single
raw `{"data": {"itemPage": ...}}` file is also accepted for spot checks.

## Why this parser's `options` shape differs from the other platforms'

Every other parser here emits a flat `options: {group_name: [option, ...]}`,
because those platforms only ever expose one level of modifiers. DoorDash
returns a *tree*: an option can carry its own modifier groups in
`nestedExtrasList`. Confirmed live on Hungry Howie's "Build Your Own" - each
size holds a full set of groups priced for that size:

    Meats            Junior   Small  Medium   Large  X-Large
      Pepperoni        1.37    1.71    1.94    2.29     2.52

Rezku needed a click-per-size to see that; here it's one response.

Flattening it into `price_by_size` (parse_rezku_menu.py's approach) is lossy,
because on DoorDash *availability* varies by size and not just price:

    Styles   Junior  -> Original Round
             Small   -> Original Round, Gluten Free Crust* (+$3.45)
             Medium  -> Original Round, Thin Crust, Stuffed Crust (+$3.44)
             X-Large -> Original Round

Merged into one list, "Stuffed Crust" would hold prices for Medium/Large and
nothing for Junior - indistinguishable from "free in Junior". Since the product
needs to answer "which sizes can I get gluten free?", that distinction is
load-bearing, so the tree is preserved verbatim in `options`.

## The three layers each item gets

- `options`    - the faithful tree. Powers the size/style picker UI.
- `option_index` - every option in the tree flattened to one row each, carrying
  the parent selections it's available under and its price under each. Powers
  search ("show me gluten free") without walking the tree.
- `dietary_badges` - derived, for result-card badges ("Gluten free available"),
  each carrying the same availability detail so the card and the picker agree.

Plus `price_min`/`price_max`, computed over *required* groups only (recursing
into the cheapest/priciest parent), so a search result can show a real range
rather than a bare "from $5.75" that no configuration can actually buy.

## Two DoorDash-specific gotchas this handles

- **Cross-sell groups are not modifiers.** A group with `type == "item"`
  ("Recommended Beverages", "Add Drinks With DoubleDash") lists *other menu
  items* as upsells - left in `options` it would make a six-pack of beer look
  like a taco topping. These are split out into `cross_sell` and excluded from
  `options`, `option_index` and pricing. The `type` field is the reliable
  discriminator; `nextCursor` is not (it's set on only some cross-sell options).
- **`dietaryTagsList` is always empty.** Checked across 1,443 options on two
  restaurants: never populated. So dietary badges are keyword-derived from
  option names, which is a heuristic - see DIETARY_PATTERNS.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterator

# Groups DoorDash marks as `item` are upsells pointing at other menu items,
# not modifiers of this one.
MODIFIER_GROUP_TYPE = "extra_option"
CROSS_SELL_GROUP_TYPE = "item"

# dietaryTagsList is never populated (verified), so these are matched against
# option names. Heuristic by nature: "Gluten Free Crust*" matches, but a
# restaurant that writes "GF crust" would not. Kept deliberately narrow -
# a false positive on a dietary badge is worse than a miss.
DIETARY_PATTERNS: list[tuple[str, str, re.Pattern[str]]] = [
    ("gluten_free", "Gluten free available", re.compile(r"gluten[\s_-]?free|\bGF\b", re.I)),
    ("vegan", "Vegan option available", re.compile(r"\bvegan\b", re.I)),
    ("vegetarian", "Vegetarian option available", re.compile(r"\bvegetarian\b", re.I)),
    ("dairy_free", "Dairy free available", re.compile(r"dairy[\s_-]?free", re.I)),
    ("cauliflower_crust", "Cauliflower crust available", re.compile(r"cauliflower", re.I)),
]


def money(unit_amount: Any) -> float:
    """DoorDash prices are integer cents."""
    try:
        return round(int(unit_amount) / 100.0, 2)
    except (TypeError, ValueError):
        return 0.0


def is_modifier(group: dict[str, Any]) -> bool:
    return (group.get("type") or MODIFIER_GROUP_TYPE) == MODIFIER_GROUP_TYPE


def build_group(group: dict[str, Any]) -> dict[str, Any]:
    """One modifier group, recursing into each option's nested groups."""
    options = []
    for opt in group.get("options") or []:
        entry: dict[str, Any] = {
            "name": opt.get("name") or "",
            "price": money(opt.get("unitAmount")),
            "description": opt.get("description") or "",
        }
        if opt.get("defaultQuantity"):
            entry["default_quantity"] = opt["defaultQuantity"]
        nested = [build_group(g) for g in (opt.get("nestedExtrasList") or []) if is_modifier(g)]
        if nested:
            entry["nested"] = nested
        options.append(entry)
    return {
        "group": group.get("name") or "Options",
        "required": not group.get("isOptional", True),
        "min_select": group.get("minNumOptions"),
        "max_select": group.get("maxNumOptions"),
        "free_count": group.get("numFreeOptions") or 0,
        "selection": group.get("selectionNode"),
        "options": options,
    }


def build_cross_sell(group: dict[str, Any]) -> dict[str, Any]:
    return {
        "group": group.get("name") or "Recommended",
        "items": [
            {"name": o.get("name") or "", "price": money(o.get("unitAmount"))}
            for o in group.get("options") or []
        ],
    }


def required_bounds(groups: list[dict[str, Any]]) -> tuple[float, float]:
    """Cheapest and priciest way to satisfy the *required* groups in `groups`,
    recursing so a required group nested under a size counts too. Optional
    groups are ignored - their max is unbounded and meaningless as a range."""
    low = high = 0.0
    for group in groups:
        if not group.get("required"):
            continue
        options = group.get("options") or []
        if not options:
            continue
        picks = group.get("min_select") or 1
        lows, highs = [], []
        for opt in options:
            nested_low, nested_high = required_bounds(opt.get("nested") or [])
            lows.append(opt["price"] + nested_low)
            highs.append(opt["price"] + nested_high)
        low += sum(sorted(lows)[:picks])
        high += sum(sorted(highs, reverse=True)[:picks])
    return round(low, 2), round(high, 2)


def walk_options(
    groups: list[dict[str, Any]],
    parent_group: str | None = None,
    parent_option: str | None = None,
) -> Iterator[tuple[dict[str, Any], dict[str, Any], str | None, str | None]]:
    """Yield (group, option, parent_group, parent_option) for the whole tree."""
    for group in groups:
        for opt in group.get("options") or []:
            yield group, opt, parent_group, parent_option
            yield from walk_options(opt.get("nested") or [], group["group"], opt["name"])


def build_option_index(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten the tree to one row per (group, option name), recording which
    parent selections it's available under and its price under each. This is
    what search queries hit - it answers "is gluten free available, and in
    which sizes?" without a tree walk."""
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for group, opt, parent_group, parent_option in walk_options(groups):
        key = (group["group"], opt["name"])
        row = index.get(key)
        if row is None:
            row = {
                "name": opt["name"],
                "group": group["group"],
                "required": group["required"],
                "parent_group": parent_group,
            }
            if parent_group is None:
                row["price"] = opt["price"]
            else:
                row["available_when"] = []
                row["price_by_parent"] = {}
            index[key] = row
        if parent_group is not None and parent_option is not None:
            row.setdefault("available_when", []).append(parent_option)
            row.setdefault("price_by_parent", {})[parent_option] = opt["price"]
    return list(index.values())


def build_dietary_badges(option_index: list[dict[str, Any]], item_text: str) -> list[dict[str, Any]]:
    badges = []
    for tag, label, pattern in DIETARY_PATTERNS:
        matches = [
            {
                "option": row["name"],
                "group": row["group"],
                "parent_group": row.get("parent_group"),
                "available_when": row.get("available_when"),
                "price_by_parent": row.get("price_by_parent"),
                "price": row.get("price"),
            }
            for row in option_index
            if pattern.search(row["name"])
        ]
        if matches:
            badges.append({"tag": tag, "label": label, "matches": matches})
        elif pattern.search(item_text):
            badges.append({"tag": tag, "label": label, "matches": []})
    return badges


def parse_item(entry: dict[str, Any]) -> dict[str, Any] | None:
    page = entry.get("item_page")
    if not page:
        return None
    header = page.get("itemHeader") or {}
    raw_groups = page.get("optionLists") or []

    groups = [build_group(g) for g in raw_groups if is_modifier(g)]
    cross_sell = [build_cross_sell(g) for g in raw_groups if (g.get("type") == CROSS_SELL_GROUP_TYPE)]

    base = money(header.get("unitAmount"))
    low, high = required_bounds(groups)
    option_index = build_option_index(groups)
    description = header.get("description") or ""
    title = header.get("name") or entry.get("name") or ""

    item: dict[str, Any] = {
        "title": title,
        "ingredients_or_description": description,
        "price": f"${base + low:.2f}",
        "price_min": round(base + low, 2),
        "price_max": round(base + high, 2),
        "options": groups,
        "option_index": option_index,
    }
    if cross_sell:
        item["cross_sell"] = cross_sell
    badges = build_dietary_badges(option_index, f"{title} {description}")
    if badges:
        item["dietary_badges"] = badges
    return item


def load_entries(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    if "items" in payload:
        return payload["items"], payload.get("source_url") or ""
    page = (payload.get("data") or {}).get("itemPage")
    if page:
        return [{"item_page": page, "section": "Uncategorized", "name": None}], ""
    return [], ""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", type=Path, help="harvest output from spike_doordash_network_capture.py")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    payload = json.loads(args.input.read_text())
    entries, source_url = load_entries(payload)

    sections: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    skipped = 0
    badge_counts: dict[str, int] = {}

    for entry in entries:
        item = parse_item(entry)
        if item is None:
            skipped += 1
            continue
        section = entry.get("section") or "Uncategorized"
        if section not in sections:
            sections[section] = []
            order.append(section)
        sections[section].append(item)
        for badge in item.get("dietary_badges") or []:
            badge_counts[badge["tag"]] = badge_counts.get(badge["tag"], 0) + 1

    output = {
        "source": {
            "response_path": str(args.input),
            "url": source_url,
            "store_id": payload.get("store_id"),
            "method": "graphql/itemPage",
        },
        "menu_sections": [{"section": name, "items": sections[name]} for name in order],
    }
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    item_count = sum(len(s["items"]) for s in output["menu_sections"])
    nested = sum(
        1
        for s in output["menu_sections"]
        for it in s["items"]
        for g in it["options"]
        for o in g["options"]
        if o.get("nested")
    )
    badge_text = ", ".join(f"{k}={v}" for k, v in sorted(badge_counts.items())) or "none"
    print(
        f"Wrote {args.output} ({len(output['menu_sections'])} sections, {item_count} items, "
        f"{nested} options with nested groups, {skipped} skipped; dietary badges: {badge_text})"
    )


if __name__ == "__main__":
    main()
