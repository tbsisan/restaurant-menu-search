#!/usr/bin/env python3
"""Extract restaurant/fast_food POIs from an OpenStreetMap XML file to JSONL.

Handles OSM elements where restaurants can be represented as:
  - node: a single lat/lon point
  - way: an ordered list of node refs, usually a building/area outline

Only matches the exact tag k="amenity" with v="restaurant" or v="fast_food".
Tags like k="disused:amenity" are intentionally ignored.
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

RESTAURANT_AMENITIES = {"restaurant", "fast_food"}
OSM_META_ATTRS = ("version", "timestamp", "changeset", "uid", "user")


def tags_for(elem: ET.Element) -> dict[str, str]:
    """Return all <tag k="..." v="..."/> children as a JSON-friendly dict."""
    tags: dict[str, str] = {}
    for tag in elem.findall("tag"):
        k = tag.get("k")
        if k is None:
            continue
        tags[k] = tag.get("v", "")
    return tags


def is_restaurant(tags: dict[str, str]) -> bool:
    """Exact active restaurant test.

    The positive match is only k="amenity" with v="restaurant" or v="fast_food".
    Lifecycle tags such as k="disused:amenity" are not positive matches. If a
    record also has disused:amenity=restaurant/fast_food, treat that as closed or
    conflicting and skip it.
    """
    return (
        tags.get("amenity") in RESTAURANT_AMENITIES
        and tags.get("disused:amenity") not in RESTAURANT_AMENITIES
    )


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


def parse_osm_restaurants(input_path: Path, output_path: Path) -> dict[str, int]:
    # OSM XML normally lists all nodes before ways, so a single pass can keep a
    # compact node-id -> coordinate lookup while streaming and clearing elements.
    node_coords: dict[str, tuple[float, float]] = {}
    stats = {
        "nodes_seen": 0,
        "ways_seen": 0,
        "restaurant_nodes": 0,
        "restaurant_ways": 0,
        "restaurant_ways_with_missing_nodes": 0,
        "records_written": 0,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as out:
        context = ET.iterparse(input_path, events=("end",))
        for _event, elem in context:
            if elem.tag == "node":
                stats["nodes_seen"] += 1
                node_id = elem.get("id")
                lat_s = elem.get("lat")
                lon_s = elem.get("lon")
                if node_id is not None and lat_s is not None and lon_s is not None:
                    lat = float(lat_s)
                    lon = float(lon_s)
                    node_coords[node_id] = (lat, lon)

                    tags = tags_for(elem)
                    if is_restaurant(tags):
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
                        out.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                        stats["restaurant_nodes"] += 1
                        stats["records_written"] += 1
                elem.clear()

            elif elem.tag == "way":
                stats["ways_seen"] += 1
                tags = tags_for(elem)
                if is_restaurant(tags):
                    way_id = elem.get("id")
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
                        "id": way_id,
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
                        stats["restaurant_ways_with_missing_nodes"] += 1

                    out.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                    stats["restaurant_ways"] += 1
                    stats["records_written"] += 1
                elem.clear()

            elif elem.tag in {"relation", "bounds", "note", "meta"}:
                # User asked for node/way restaurants only; clear other top-level elements.
                elem.clear()

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input",
        nargs="?",
        default="/home/tbsisan/Projects/restaurant-menu-search/external-data/raw-untracked/downriver.xml",
        help="Input OSM XML file",
    )
    parser.add_argument(
        "output",
        nargs="?",
        default="/home/tbsisan/Projects/restaurant-menu-search/external-data/derived/downriver-restaurants.jsonl",
        help="Output JSONL file",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    if not input_path.exists():
        print(f"Input not found: {input_path}", file=sys.stderr)
        return 2

    stats = parse_osm_restaurants(input_path, output_path)
    for key, value in stats.items():
        print(f"{key}: {value}")
    print(f"output: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
