#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def normalize_item(item):
    return {
        "platform_item_id": clean(item.get("id") or item.get("platform_item_id")),
        "name": clean(item.get("name")),
        "description": clean(item.get("description")),
        "price_text": clean(item.get("price") or item.get("price_text")),
        "raw_text": clean(item.get("button_text") or item.get("raw_text")),
        "source_category_id": clean(item.get("category_id") or item.get("source_category_id")),
    }


def normalize_section(section):
    seen = set()
    items = []
    for item in section.get("items", []):
        normalized = normalize_item(item)
        key = (
            normalized["platform_item_id"],
            normalized["name"],
            normalized["price_text"],
        )
        if key in seen:
            continue
        seen.add(key)
        items.append(normalized)

    section_id = clean(section.get("id") or section.get("platform_section_id"))
    if not section_id and items:
        section_id = items[0]["source_category_id"]

    return {
        "name": clean(section.get("title") or section.get("name")),
        "platform_section_id": section_id,
        "items": items,
    }


def collect_raw_artifacts(raw_path, raw):
    artifacts = [str(raw_path)]

    raw_dir = raw_path.parent
    for sibling_name in (
        "grubhub-scroll-extracted-menu-raw.txt",
        "grubhub-from-scratch-scroll-observations.json",
        "grubhub-menu-layout-notes.md",
    ):
        sibling = raw_dir / sibling_name
        if sibling.exists():
            artifacts.append(str(sibling))

    observed_path = clean(raw.get("observation_path"))
    if observed_path:
        local_observation = raw_dir / Path(observed_path).name
        if local_observation.exists():
            observed_path = str(local_observation)
        if observed_path not in artifacts:
            artifacts.append(observed_path)

    return artifacts


def main():
    parser = argparse.ArgumentParser(
        description="Normalize raw Grubhub scroll extraction into project menu JSON."
    )
    parser.add_argument("--raw", required=True, help="Raw scroll extraction JSON path")
    parser.add_argument("--restaurant-slug", required=True)
    parser.add_argument("--restaurant-name", required=True)
    parser.add_argument("--platform-name", default="")
    parser.add_argument("--url", default="")
    parser.add_argument("--address", default="")
    parser.add_argument("--out", required=True, help="Final grubhub-menu-<slug>.json path")
    args = parser.parse_args()

    raw_path = Path(args.raw)
    raw = json.loads(raw_path.read_text(encoding="utf-8"))

    sections = [normalize_section(section) for section in raw.get("sections", [])]
    sections = [section for section in sections if section["name"] or section["items"]]

    raw_artifacts = collect_raw_artifacts(raw_path, raw)

    output = {
        "source": "grubhub",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "restaurant": {
            "name": args.restaurant_name,
            "slug": args.restaurant_slug,
            "platform_name": args.platform_name or args.restaurant_name,
            "url": args.url,
            "address": args.address,
        },
        "menu": {
            "sections": sections,
        },
        "raw_artifacts": raw_artifacts,
        "extraction_notes": {
            "method": raw.get("source", "Grubhub scroll extraction"),
            "observation_path": next(
                (
                    path
                    for path in raw_artifacts
                    if path.endswith("grubhub-from-scratch-scroll-observations.json")
                ),
                raw.get("observation_path", ""),
            ),
            "canonicalized": False,
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    item_count = sum(len(section["items"]) for section in sections)
    print(f"Wrote {out_path} with {len(sections)} sections and {item_count} items")


if __name__ == "__main__":
    main()
