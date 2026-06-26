#!/usr/bin/env python3
"""Tabulate cuisine and diet tags from the downriver restaurants JSONL."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DEFAULT_INPUT = PROJECT_ROOT / "external-data" / "derived-untracked" / "downriver-restaurants.jsonl"
DEFAULT_OUTPUT = PROJECT_ROOT / "external-data" / "derived" / "downriver-cuisine-diet-counts.json"
DEFAULT_CUISINE_LIST_OUTPUT = PROJECT_ROOT / "external-data" / "derived" / "downriver-restaurants-with-cuisines.txt"
DEFAULT_UNKNOWN_OUTPUT = PROJECT_ROOT / "external-data" / "derived" / "downriver-restaurants-unknown-cuisines.txt"
DEFAULT_NO_NAME_OUTPUT = PROJECT_ROOT / "external-data" / "derived" / "downriver-restaurants-without-name.jsonl"
PRESENT_DIET_VALUES = {"yes", "only"}


def normalize_token(value: str) -> str:
    return value.strip().lower()


def display_label(value: str) -> str:
    return value.strip().replace("_", " ").title()


def extract_cuisines(tags: dict[str, Any]) -> list[str]:
    cuisine_value = tags.get("cuisine")
    if not cuisine_value:
        return []
    cuisines = []
    for token in str(cuisine_value).split(";"):
        normalized = normalize_token(token)
        if normalized:
            cuisines.append(normalized)
    return cuisines


def extract_diets(tags: dict[str, Any]) -> list[str]:
    diets: set[str] = set()

    direct_diet = tags.get("diet")
    if direct_diet and direct_diet != "subtype":
        normalized = normalize_token(str(direct_diet))
        if normalized:
            diets.add(normalized)

    for key, value in tags.items():
        if not key.startswith("diet:"):
            continue
        if normalize_token(str(value)) not in PRESENT_DIET_VALUES:
            continue
        diet_type = normalize_token(key.split(":", 1)[1])
        if diet_type:
            diets.add(diet_type)

    return sorted(diets)


def display_name(tags: dict[str, Any], record: dict[str, Any]) -> str | None:
    for key in ("name", "brand", "official_name", "operator"):
        value = tags.get(key)
        if value:
            return str(value).strip()
    record_id = record.get("id")
    if record_id is None:
        return None
    return f"Unnamed {record.get('type', 'record')} {record_id}"


def tabulate(input_path: Path) -> dict[str, Any]:
    cuisine_counts: Counter[str] = Counter()
    diet_counts: Counter[str] = Counter()
    cuisine_lines: list[str] = []
    unknown_cuisine_names: list[str] = []
    missing_name_records: list[dict[str, Any]] = []
    stats = {
        "records_read": 0,
        "records_with_cuisine": 0,
        "records_with_diet": 0,
        "records_with_name_and_cuisine": 0,
        "records_with_unknown_cuisine": 0,
        "records_without_name": 0,
    }

    with input_path.open(encoding="utf-8") as src:
        for line in src:
            line = line.strip()
            if not line:
                continue
            stats["records_read"] += 1
            record = json.loads(line)
            tags = record.get("tags", {})
            if not isinstance(tags, dict):
                continue

            cuisines = extract_cuisines(tags)
            diets = extract_diets(tags)
            name = display_name(tags, record)
            raw_name = tags.get("name")

            if not raw_name:
                stats["records_without_name"] += 1
                missing_name_records.append(record)

            if cuisines:
                stats["records_with_cuisine"] += 1
                cuisine_counts.update(cuisines)
                if name:
                    cuisine_text = "; ".join(display_label(cuisine) for cuisine in cuisines)
                    cuisine_lines.append(f"{name} ({cuisine_text})")
                    stats["records_with_name_and_cuisine"] += 1
            elif name:
                unknown_cuisine_names.append(name)
                stats["records_with_unknown_cuisine"] += 1

            if diets:
                stats["records_with_diet"] += 1
                diet_counts.update(diets)

    return {
        "source_file": str(input_path),
        "summary": stats,
        "cuisine_counts": dict(sorted(cuisine_counts.items())),
        "diet_counts": dict(sorted(diet_counts.items())),
        "cuisine_lines": cuisine_lines,
        "unknown_cuisine_names": unknown_cuisine_names,
        "missing_name_records": missing_name_records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", default=str(DEFAULT_INPUT), help="Input JSONL path")
    parser.add_argument("output", nargs="?", default=str(DEFAULT_OUTPUT), help="Output JSON path")
    parser.add_argument(
        "--cuisine-list-output",
        default=str(DEFAULT_CUISINE_LIST_OUTPUT),
        help="Output text file for 'Name (Cuisine)' lines",
    )
    parser.add_argument(
        "--unknown-output",
        default=str(DEFAULT_UNKNOWN_OUTPUT),
        help="Output text file for restaurant names with no cuisine",
    )
    parser.add_argument(
        "--no-name-output",
        default=str(DEFAULT_NO_NAME_OUTPUT),
        help="Output JSONL file for records with no name field",
    )
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    cuisine_list_output = Path(args.cuisine_list_output).expanduser().resolve()
    unknown_output = Path(args.unknown_output).expanduser().resolve()
    no_name_output = Path(args.no_name_output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cuisine_list_output.parent.mkdir(parents=True, exist_ok=True)
    unknown_output.parent.mkdir(parents=True, exist_ok=True)
    no_name_output.parent.mkdir(parents=True, exist_ok=True)

    results = tabulate(input_path)
    with output_path.open("w", encoding="utf-8") as out:
        json.dump(results, out, indent=2, sort_keys=True, ensure_ascii=False)
        out.write("\n")
    with cuisine_list_output.open("w", encoding="utf-8") as out:
        for line in results["cuisine_lines"]:
            out.write(f"{line}\n")
    with unknown_output.open("w", encoding="utf-8") as out:
        for name in results["unknown_cuisine_names"]:
            out.write(f"{name}\n")
    with no_name_output.open("w", encoding="utf-8") as out:
        for record in results["missing_name_records"]:
            out.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            out.write("\n")

    print(f"output: {output_path}")
    print(f"cuisine_list_output: {cuisine_list_output}")
    print(f"unknown_output: {unknown_output}")
    print(f"no_name_output: {no_name_output}")
    print(f"records_read: {results['summary']['records_read']}")
    print(f"cuisine_types: {len(results['cuisine_counts'])}")
    print(f"diet_types: {len(results['diet_counts'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
