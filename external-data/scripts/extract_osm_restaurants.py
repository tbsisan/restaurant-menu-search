#!/usr/bin/env python3
"""Extract restaurant/fast_food POIs from an OpenStreetMap XML file to JSONL.

Handles OSM elements where restaurants can be represented as:
  - node: a single lat/lon point
  - way: an ordered list of node refs, usually a building/area outline

Matches the exact tag k="amenity" with restaurant, fast_food, or several other
food-related values, including semicolon-delimited amenity values. Also matches
shop=restaurant, food=yes, and places that have a cuisine or diet tag.
Tags like k="disused:amenity" are intentionally ignored.
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
# Note we need to do additional research on certain types of shops like convenience stores.
# `shop=coffee` and `shop=chocolate` are included because small local samples
# showed likely walk-in consumable businesses, but larger-region runs should
# verify these are selling consumables to walk-in customers.
RESTAURANT_AMENITIES = {
    "restaurant",
    "fast_food",
    "bar",
    "biergarten",
    "cafe",
    "pub",
    "ice_cream",
    "canteen",
}
RESTAURANT_SHOPS = {
    "restaurant",
    "fast_food",
    "bakery",
    "confectionery",
    "coffee",
    "chocolate",
    "pastry",
    "deli",
    "tea",
    "seafood",
}
HAS_FOOD = {"yes"}
OSM_META_ATTRS = ("version", "timestamp", "changeset", "uid", "user")
DEFAULT_INPUT = PROJECT_ROOT / "external-data" / "raw-untracked" / "downriver.xml"
DEFAULT_OUTPUT = PROJECT_ROOT / "external-data" / "derived-untracked" / "downriver-restaurants.jsonl"
DEFAULT_COUNTS_OUTPUT = PROJECT_ROOT / "external-data" / "derived-untracked" / "downriver-osm-tag-counts.json"
DEFAULT_KITCHEN_OUTPUT = PROJECT_ROOT / "external-data" / "derived-untracked" / "downriver-osm-kitchens.jsonl"
DEFAULT_DAIRY_OUTPUT = PROJECT_ROOT / "external-data" / "derived-untracked" / "downriver-osm-dairies.jsonl"
KITCHEN_RESTAURANT_HINTS = {
    "bbq",
    "bistro",
    "burger",
    "burrito",
    "cafe",
    "cantina",
    "chicken",
    "coffee",
    "deli",
    "diner",
    "eatery",
    "grill",
    "gyro",
    "kebab",
    "mexican",
    "pizzeria",
    "pizza",
    "pub",
    "restaurant",
    "sandwich",
    "seafood",
    "shack",
    "sushi",
    "taco",
    "taqueria",
    "wings",
}


def split_tag_values(value: Any) -> list[str]:
    """Split semicolon-delimited OSM tag values into normalized non-empty tokens."""
    if value is None:
        return []
    return [token.strip().lower() for token in str(value).split(";") if token.strip()]


def tags_for(elem: ET.Element) -> dict[str, str]:
    """Return all <tag k="..." v="..."/> children as a JSON-friendly dict."""
    tags: dict[str, str] = {}
    for tag in elem.findall("tag"):
        k = tag.get("k")
        if k is None:
            continue
        if k.startswith("diet:"):
            tags["diet"] = "subtype"
        tags[k] = tag.get("v", "")
    return tags


def is_restaurant(tags: dict[str, str]) -> bool:
    """Active restaurant test.

    Positive amenity and shop matches support semicolon-delimited values.
    Lifecycle tags such as k="disused:amenity" are not positive matches. If a
    record also has disused:amenity=restaurant/fast_food, treat that as closed or
    conflicting and skip it. Note: dict.get() does exact matches so we don't need
    to test for keys with a disused prefix. Positive matching keys is enough
    """
    return (
        bool(set(split_tag_values(tags.get("amenity"))) & RESTAURANT_AMENITIES)
        or bool(set(split_tag_values(tags.get("shop"))) & RESTAURANT_SHOPS)
        or tags.get("food") in HAS_FOOD
        or tags.get("cuisine")
        or tags.get("diet")
        #and tags.get("disused:amenity") not in RESTAURANT_AMENITIES
    )


def has_kitchen_shop(tags: dict[str, str]) -> bool:
    return "kitchen" in split_tag_values(tags.get("shop"))


def has_dairy_shop(tags: dict[str, str]) -> bool:
    return "dairy" in split_tag_values(tags.get("shop"))


def kitchen_restaurant_hint(tags: dict[str, str]) -> dict[str, Any]:
    text_parts = []
    for key in ("name", "brand", "official_name", "operator", "description"):
        value = tags.get(key)
        if value:
            text_parts.append(str(value).strip())

    combined_text = " ".join(text_parts).lower()
    matched_hints = sorted(
        hint for hint in KITCHEN_RESTAURANT_HINTS if combined_text and hint in combined_text
    )

    return {
        "possible_restaurant": bool(matched_hints),
        "matched_hints": matched_hints,
        "searched_text": combined_text,
    }


def osm_attrs(elem: ET.Element) -> dict[str, str]:
    """Keep useful OSM metadata attributes when present."""
    return {key: elem.attrib[key] for key in OSM_META_ATTRS if key in elem.attrib}


def centroid(points: list[dict[str, float]]) -> dict[str, float] | None:
    if not points:
        return None
    return {
        "lat": sum(p["lat"] for p in points) / len(points),
        "lon": sum(p["lon"] for p in points) / len(points),
    }


def count_tag_values(counter: Counter[str], tags: dict[str, str], key: str) -> None:
    counter.update(split_tag_values(tags.get(key)))


def sort_counts_desc(counter: Counter[str]) -> dict[str, int]:
    return dict(sorted(counter.items(), key=lambda item: (-item[1], item[0])))


def build_node_record(
    elem: ET.Element,
    node_id: str,
    lat: float,
    lon: float,
    tags: dict[str, str],
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "type": "node",
        "id": node_id,
        "lat": lat,
        "lon": lon,
        "tags": tags,
    }
    attrs = osm_attrs(elem)
    if attrs:
        record["osm"] = attrs
    return record


def build_way_record(
    elem: ET.Element,
    node_coords: dict[str, tuple[float, float]],
    tags: dict[str, str],
) -> tuple[dict[str, Any], list[str]]:
    refs = [nd.get("ref") for nd in elem.findall("nd") if nd.get("ref")]
    geometry: list[dict[str, float]] = []
    missing_refs: list[str] = []
    for ref in refs:
        coords = node_coords.get(ref)
        if coords is None:
            missing_refs.append(ref)
        else:
            lat, lon = coords
            geometry.append({"lat": lat, "lon": lon})

    record = {
        "type": "way",
        "id": elem.get("id"),
        "node_refs": refs,
        "geometry": geometry,
        "centroid": centroid(geometry),
        "tags": tags,
    }
    attrs = osm_attrs(elem)
    if attrs:
        record["osm"] = attrs
    if missing_refs:
        record["missing_node_refs"] = missing_refs
    return record, missing_refs


def parse_osm_restaurants(
    input_path: Path,
    output_path: Path,
    kitchen_output_path: Path,
    dairy_output_path: Path,
) -> dict[str, Any]:
    # OSM XML normally lists all nodes before ways, so a single pass can keep a
    # compact node-id -> coordinate lookup while streaming and clearing elements.
    node_coords: dict[str, tuple[float, float]] = {}
    stats = {
        "nodes_seen": 0,
        "ways_seen": 0,
        "restaurant_nodes": 0,
        "restaurant_ways": 0,
        "restaurant_ways_with_missing_nodes": 0,
        "cuisine_with_no_amenity": 0,
        "diet_with_no_amenity": 0,
        "kitchen_nodes_for_review": 0,
        "kitchen_ways_for_review": 0,
        "dairy_nodes_for_review": 0,
        "dairy_ways_for_review": 0,
        "records_written": 0,
    }
    amenity_counts: Counter[str] = Counter()
    shop_counts: Counter[str] = Counter()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    kitchen_output_path.parent.mkdir(parents=True, exist_ok=True)
    dairy_output_path.parent.mkdir(parents=True, exist_ok=True)

    with (
        output_path.open("w", encoding="utf-8") as out,
        kitchen_output_path.open("w", encoding="utf-8") as kitchen_out,
        dairy_output_path.open("w", encoding="utf-8") as dairy_out,
    ):
        context = ET.iterparse(input_path, events=("end",))
        for _event, elem in context:
            if elem.tag == "node":
                stats["nodes_seen"] += 1
                tags = tags_for(elem)
                count_tag_values(amenity_counts, tags, "amenity")
                count_tag_values(shop_counts, tags, "shop")
                node_id = elem.get("id")
                lat_s = elem.get("lat")
                lon_s = elem.get("lon")
                if node_id is not None and lat_s is not None and lon_s is not None:
                    lat = float(lat_s)
                    lon = float(lon_s)
                    node_coords[node_id] = (lat, lon)

                    if has_kitchen_shop(tags):
                        kitchen_record = build_node_record(elem, node_id, lat, lon, tags)
                        kitchen_record["kitchen_review"] = kitchen_restaurant_hint(tags)
                        kitchen_out.write(json.dumps(kitchen_record, ensure_ascii=False, sort_keys=True) + "\n")
                        stats["kitchen_nodes_for_review"] += 1
                    if has_dairy_shop(tags):
                        dairy_record = build_node_record(elem, node_id, lat, lon, tags)
                        dairy_out.write(json.dumps(dairy_record, ensure_ascii=False, sort_keys=True) + "\n")
                        stats["dairy_nodes_for_review"] += 1

                    if is_restaurant(tags):
                        record = build_node_record(elem, node_id, lat, lon, tags)
                        out.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                        if "diet" in tags and "amenity" not in tags:
                            stats["diet_with_no_amenity"] += 1
                        if "cuisine" in tags and "amenity" not in tags:
                            #print(f"{tags['name']} has cuisine {tags['cuisine']}")
                            print(json.dumps(tags, indent=4))
                            stats["cuisine_with_no_amenity"] += 1
                        stats["restaurant_nodes"] += 1
                        stats["records_written"] += 1
                elem.clear()

            elif elem.tag == "way":
                stats["ways_seen"] += 1
                tags = tags_for(elem)
                count_tag_values(amenity_counts, tags, "amenity")
                count_tag_values(shop_counts, tags, "shop")
                if has_kitchen_shop(tags):
                    kitchen_record, missing_refs = build_way_record(elem, node_coords, tags)
                    kitchen_record["kitchen_review"] = kitchen_restaurant_hint(tags)
                    kitchen_out.write(json.dumps(kitchen_record, ensure_ascii=False, sort_keys=True) + "\n")
                    stats["kitchen_ways_for_review"] += 1
                if has_dairy_shop(tags):
                    dairy_record, missing_refs = build_way_record(elem, node_coords, tags)
                    dairy_out.write(json.dumps(dairy_record, ensure_ascii=False, sort_keys=True) + "\n")
                    stats["dairy_ways_for_review"] += 1
                if is_restaurant(tags):
                    record, missing_refs = build_way_record(elem, node_coords, tags)
                    if missing_refs:
                        stats["restaurant_ways_with_missing_nodes"] += 1

                    out.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                    if "diet" in tags and "amenity" not in tags:
                        stats["diet_with_no_amenity"] += 1
                    if "cuisine" in tags and "amenity" not in tags:
                        #print(f"{tags['name']} has cuisine {tags['cuisine']}")
                        print(json.dumps(tags, indent=4))
                        stats["cuisine_with_no_amenity"] += 1
                    stats["restaurant_ways"] += 1
                    stats["records_written"] += 1
                elem.clear()

            elif elem.tag in {"relation", "bounds", "note", "meta"}:
                # User asked for node/way restaurants only; clear other top-level elements.
                elem.clear()

    return {
        **stats,
        "amenity_counts": sort_counts_desc(amenity_counts),
        "shop_counts": sort_counts_desc(shop_counts),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input",
        nargs="?",
        default=str(DEFAULT_INPUT),
        help="Input OSM XML file",
    )
    parser.add_argument(
        "output",
        nargs="?",
        default=str(DEFAULT_OUTPUT),
        help="Output JSONL file",
    )
    parser.add_argument(
        "--counts-output",
        default=str(DEFAULT_COUNTS_OUTPUT),
        help="Output JSON file for amenity/shop count summaries",
    )
    parser.add_argument(
        "--kitchen-output",
        default=str(DEFAULT_KITCHEN_OUTPUT),
        help="Output JSONL file for shop=kitchen records to review later",
    )
    parser.add_argument(
        "--dairy-output",
        default=str(DEFAULT_DAIRY_OUTPUT),
        help="Output JSONL file for shop=dairy records to review before inclusion",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    counts_output_path = Path(args.counts_output)
    kitchen_output_path = Path(args.kitchen_output)
    dairy_output_path = Path(args.dairy_output)
    if not input_path.exists():
        print(f"Input not found: {input_path}", file=sys.stderr)
        return 2

    stats = parse_osm_restaurants(input_path, output_path, kitchen_output_path, dairy_output_path)
    counts_output_path.parent.mkdir(parents=True, exist_ok=True)
    with counts_output_path.open("w", encoding="utf-8") as out:
        json.dump(
            {
                "input": str(input_path),
                "restaurants_output": str(output_path),
                "amenity_counts": stats["amenity_counts"],
                "shop_counts": stats["shop_counts"],
            },
            out,
            indent=2,
            ensure_ascii=False,
        )
        out.write("\n")

    for key, value in stats.items():
        if isinstance(value, dict):
            print(f"{key}: {json.dumps(value, sort_keys=True)}")
        else:
            print(f"{key}: {value}")
    print(f"output: {output_path}")
    print(f"counts_output: {counts_output_path}")
    print(f"kitchen_output: {kitchen_output_path}")
    print(f"dairy_output: {dairy_output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
