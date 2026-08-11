#!/usr/bin/env python3
"""Extract review/rating signals from saved review spike pages."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "external-data/review-scraping/camino_real_wyandotte_spike"
RATING_RE = re.compile(r"\b([1-5](?:\.\d)?)\s*(?:out of\s*)?(?:/|of)?\s*5\s*(?:stars?)?\b", re.I)
COUNT_RE = re.compile(r"\b(\d[\d,]*)\s+(reviews?|ratings?)\b", re.I)
REVIEWISH_RE = re.compile(r"review|rating|stars?|customer|google|yelp|tripadvisor|facebook|doordash|grubhub|uber", re.I)


def clean_text(raw_html: str) -> str:
    soup = BeautifulSoup(raw_html, "lxml")
    for node in soup(["script", "style", "noscript", "svg"]):
        node.decompose()
    lines = []
    for line in soup.get_text("\n").splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def parse_jsonish(raw: str) -> Any | None:
    raw = raw.strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        unescaped = html.unescape(raw)
        if unescaped != raw:
            try:
                return json.loads(unescaped)
            except json.JSONDecodeError:
                return None
    return None


def flatten(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        out = [value]
        for child in value.values():
            out.extend(flatten(child))
        return out
    if isinstance(value, list):
        out: list[dict[str, Any]] = []
        for child in value:
            out.extend(flatten(child))
        return out
    return []


def short(value: Any, limit: int = 1000) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    text = re.sub(r"\s+", " ", text)
    return text[:limit]


def extract_json_blocks(soup: BeautifulSoup) -> list[dict[str, Any]]:
    blocks = []
    for script in soup.find_all("script"):
        raw = script.string or script.get_text()
        data = parse_jsonish(raw)
        if data is None:
            continue
        blocks.append(
            {
                "id": script.get("id") or "",
                "type": script.get("type") or "",
                "src": script.get("src") or "",
                "data": data,
            }
        )
    return blocks


def extract_signals(path: Path) -> dict[str, Any]:
    raw_html = path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(raw_html, "lxml")
    text = clean_text(raw_html)
    json_blocks = extract_json_blocks(soup)
    structured_ratings = []
    review_objects = []
    ratingish_objects = []
    for block in json_blocks:
        for obj in flatten(block["data"]):
            aggregate = obj.get("aggregateRating")
            if isinstance(aggregate, dict):
                structured_ratings.append(
                    {
                        "script_id": block["id"],
                        "script_type": block["type"],
                        "name": obj.get("name"),
                        "ratingValue": aggregate.get("ratingValue"),
                        "reviewCount": aggregate.get("reviewCount") or aggregate.get("ratingCount"),
                        "bestRating": aggregate.get("bestRating"),
                        "raw": aggregate,
                    }
                )
            if any(key.lower() == "review" for key in obj):
                review_objects.append({"script_id": block["id"], "script_type": block["type"], "context": short(obj)})
            keys = " ".join(str(key) for key in obj.keys())
            if REVIEWISH_RE.search(keys) or REVIEWISH_RE.search(short(obj, 400)):
                ratingish_objects.append({"script_id": block["id"], "script_type": block["type"], "context": short(obj, 1400)})
    rating_candidates = [
        {"rating": m.group(1), "context": context(text, m.start())}
        for m in RATING_RE.finditer(text)
    ][:25]
    count_candidates = [
        {"count": m.group(1), "kind": m.group(2), "context": context(text, m.start())}
        for m in COUNT_RE.finditer(text)
    ][:25]
    review_lines = []
    for line in text.splitlines():
        if REVIEWISH_RE.search(line) and line not in review_lines:
            review_lines.append(line[:800])
        if len(review_lines) >= 80:
            break
    text_path = path.with_suffix(".parsed-text.txt")
    text_path.write_text(text + "\n", encoding="utf-8")
    return {
        "file": str(path.relative_to(ROOT)),
        "title": soup.title.get_text(" ", strip=True) if soup.title else "",
        "text_path": str(text_path.relative_to(ROOT)),
        "html_chars": len(raw_html),
        "text_chars": len(text),
        "json_script_count": len(json_blocks),
        "structured_ratings": structured_ratings,
        "rating_candidates": rating_candidates,
        "count_candidates": count_candidates,
        "review_objects": review_objects[:40],
        "ratingish_objects": ratingish_objects[:80],
        "review_lines": review_lines,
    }


def context(text: str, pos: int) -> str:
    start = max(0, pos - 180)
    end = min(len(text), pos + 260)
    return re.sub(r"\s+", " ", text[start:end]).strip()


def main() -> None:
    results = []
    for path in sorted(DEFAULT_INPUT.glob("*.html")):
        results.append(extract_signals(path))
    output = DEFAULT_INPUT / "parsed-review-signals.json"
    output.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    combined = DEFAULT_INPUT / "camino-real-wyandotte-review-signal-summary.md"
    chunks = ["# Camino Real Wyandotte Review Signal Summary", ""]
    for result in results:
        chunks.extend(
            [
                f"## {Path(result['file']).name}",
                f"- Title: {result['title']}",
                f"- HTML chars: {result['html_chars']}; text chars: {result['text_chars']}; JSON scripts: {result['json_script_count']}",
                f"- Structured ratings: {json.dumps(result['structured_ratings'], ensure_ascii=False)}",
                f"- Rating candidates: {json.dumps(result['rating_candidates'][:8], ensure_ascii=False)}",
                f"- Count candidates: {json.dumps(result['count_candidates'][:8], ensure_ascii=False)}",
                "",
                "Review/rating lines:",
            ]
        )
        chunks.extend(f"- {line}" for line in result["review_lines"][:30])
        chunks.append("")
    combined.write_text("\n".join(chunks), encoding="utf-8")
    print(output.relative_to(ROOT))
    print(combined.relative_to(ROOT))


if __name__ == "__main__":
    main()
