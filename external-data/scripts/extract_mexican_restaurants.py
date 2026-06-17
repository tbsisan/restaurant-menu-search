#!/usr/bin/env python3
"""Extract likely Mexican restaurants from downriver-restaurants.jsonl.

Rules:
  1. Always include cuisine values containing "mexican".
  2. Include cuisine values containing "tex-mex" / "tex mex".
  3. Include records whose name/brand/website/url fields look Mexican by
     specific restaurant terms, e.g. taco, taqueria, burrito, chipotle, qdoba.
  4. Include a small set of strong Spanish/Mexican name patterns found in this
     file when cuisine is missing, with lower confidence noted in match info.

The output preserves the full original OSM-derived JSON object and adds a
"mexican_match" object explaining why the record was selected.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

TEXT_FIELDS = (
    "name",
    "brand",
    "operator",
    "official_name",
    "website",
    "url",
    "contact:website",
)

# High-confidence words that indicate Mexican / Mexican-adjacent restaurants
# from name, brand, or URL. These are kept specific to avoid false matches like
# La Pita, Hook & Reel, or TGI Friday's.
HIGH_CONFIDENCE_PATTERNS = [
    ("mexican", re.compile(r"\bmexican\b|\bmexicana\b|\bmexicano\b|\bmexi\b", re.I)),
    ("taqueria", re.compile(r"\btaquer[íi]a\b", re.I)),
    ("taco", re.compile(r"\btacos?\b|\btacobell\b", re.I)),
    ("burrito", re.compile(r"\bburritos?\b", re.I)),
    ("chipotle", re.compile(r"\bchipotle\b", re.I)),
    ("qdoba", re.compile(r"\bqdoba\b", re.I)),
    ("del taco", re.compile(r"\bdel\s+taco\b", re.I)),
    ("quesada", re.compile(r"\bquesada\b", re.I)),
    ("guac", re.compile(r"\bguac\b|\bguacamole\b", re.I)),
    ("jalapeno", re.compile(r"\bjalape[nñ]o\b", re.I)),
]

# Names in this data where cuisine is missing/non-Mexican but name/URL strongly
# suggests a Mexican or Mexican-adjacent place. Kept explicit instead of using
# broad "El/La/Los/Las" matching, which produced too many false positives.
LOWER_CONFIDENCE_NAME_PATTERNS = [
    ("catrina", re.compile(r"\bcatrina'?s\b", re.I)),
    ("el barzon", re.compile(r"\bel\s+barz[oó]n\b", re.I)),
    ("el parian", re.compile(r"\bel\s+pari[aá]n\b", re.I)),
    ("la esquinita", re.compile(r"\bla\s+esquinita\b", re.I)),
    ("la noria", re.compile(r"\bla\s+noria\b", re.I)),
    ("mangonadas", re.compile(r"\bmangonadas\b", re.I)),
]


def searchable_text(tags: dict[str, Any]) -> str:
    return " ".join(str(tags.get(field, "")) for field in TEXT_FIELDS if tags.get(field))


def mexican_match(record: dict[str, Any]) -> dict[str, Any] | None:
    tags = record.get("tags", {})
    cuisine = str(tags.get("cuisine", ""))
    text = searchable_text(tags)
    reasons: list[str] = []
    confidence = "high"

    if re.search(r"\bmexican\b", cuisine, re.I):
        reasons.append(f"cuisine={cuisine!r} contains mexican")
    if re.search(r"\btex[- ]mex\b", cuisine, re.I):
        reasons.append(f"cuisine={cuisine!r} contains tex-mex")

    for label, pattern in HIGH_CONFIDENCE_PATTERNS:
        if pattern.search(text):
            reasons.append(f"name/url keyword: {label}")

    if not reasons:
        low_reasons = []
        for label, pattern in LOWER_CONFIDENCE_NAME_PATTERNS:
            if pattern.search(text):
                low_reasons.append(f"name/url looks Mexican: {label}")
        if low_reasons:
            reasons.extend(low_reasons)
            confidence = "likely"

    if not reasons:
        return None

    return {
        "confidence": confidence,
        "reasons": sorted(set(reasons)),
        "searched_text": text,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input",
        nargs="?",
        default="/home/tbsisan/Projects/restaurant-menu-search/external-data/derived/downriver-restaurants.jsonl",
        help="Input restaurants JSONL file",
    )
    parser.add_argument(
        "output",
        nargs="?",
        default="/home/tbsisan/Projects/restaurant-menu-search/external-data/derived-untracked/downriver-mexican-restaurants.jsonl",
        help="Output likely Mexican restaurants JSONL file",
    )
    args = parser.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)
    counts = {"read": 0, "written": 0, "high": 0, "likely": 0}

    with in_path.open(encoding="utf-8") as src, out_path.open("w", encoding="utf-8") as out:
        for line in src:
            counts["read"] += 1
            record = json.loads(line)
            match = mexican_match(record)
            if match is None:
                continue
            record = dict(record)
            record["mexican_match"] = match
            out.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            counts["written"] += 1
            counts[match["confidence"]] += 1

    for key, value in counts.items():
        print(f"{key}: {value}")
    print(f"output: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
