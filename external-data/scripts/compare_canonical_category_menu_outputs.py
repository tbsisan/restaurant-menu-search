#!/usr/bin/env python3
"""Compare canonical-category menu outputs from multiple models."""

from __future__ import annotations

import argparse
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_DIR = ROOT / "external-data/menu-scraping/canonical_openrouter"
DEFAULT_PATTERN = "canonical-category-v2-menu-flyer-2-gemini-pro-*.txt"
DEFAULT_OUTPUT = DEFAULT_INPUT_DIR / "canonical-category-v2-menu-flyer-2-gemini-pro-comparison.md"


@dataclass(frozen=True)
class Item:
    dish: str
    original_category: str
    canonical_category: str
    price: str
    sides_number: str
    side_choices: str
    description: str

    @property
    def key(self) -> tuple[str, str]:
        return normalize_name(self.dish), normalize_original_category(self.original_category)


def normalize_name(value: str) -> str:
    value = value.strip().lower().replace("&", "and")
    value = re.sub(r"[^a-z0-9/() ]+", "", value)
    value = re.sub(r"\s+", " ", value)
    value = value.replace("enchilada/enchilada suizas", "enchilada")
    value = value.replace("2 burritos", "burritos")
    if value in {"beans refried or charro", "refried or charro beans"}:
        return "beans"
    if value in {"rice spanish or cilantro lime", "spanish or cilantro lime rice"}:
        return "rice"
    return value


def normalize_original_category(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9 ]+", "", value)
    value = re.sub(r"\s+", " ", value)
    if value in {"family packs", "family meals"}:
        return "family pack"
    return value


def normalize_price(value: str) -> str:
    match = re.search(r"\$?\s*(\d+(?:\.\d{1,2})?)", value.strip())
    if not match:
        return value.strip()
    return f"${float(match.group(1)):.2f}"


def normalize_text(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9, ]+", "", value)
    return re.sub(r"\s+", " ", value)


def model_label(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"<!-- model: (.*?) -->", text)
    if match:
        return match.group(1)
    return path.stem


def parse_items(path: Path) -> tuple[list[Item], int, int]:
    items = []
    raw_rows = 0
    malformed_rows = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("<!--"):
            continue
        if re.fullmatch(r"\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?", line):
            continue
        parts = [part.strip() for part in line.strip("|").split("|")]
        if [part.lower() for part in parts] == [
            "dish name",
            "original category",
            "canonical category",
            "base price",
            "sides number",
            "side choices",
            "description",
        ]:
            continue
        raw_rows += 1
        if len(parts) == 7:
            items.append(Item(*parts))
        else:
            malformed_rows += 1
    return items, raw_rows, malformed_rows


def escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", "<br>")


def table(headers: list[str], rows: list[list[str]]) -> str:
    out = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    out.extend("| " + " | ".join(escape_cell(cell) for cell in row) + " |" for row in rows)
    return "\n".join(out)


def grouped_values(present: dict[str, Item], attr: str, normalizer) -> str:
    groups = defaultdict(list)
    for model, item in present.items():
        groups[normalizer(getattr(item, attr))].append(model)
    return "; ".join(f"{value or '[blank]'}: {', '.join(sorted(models))}" for value, models in sorted(groups.items()))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--pattern", default=DEFAULT_PATTERN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--source-label", default="menu-flyer-2-google__gemini-3.1-pro-preview.md")
    parser.add_argument(
        "--split-check",
        default="beans,rice,papas",
        help="Comma-separated normalized dish names expected to be split, or empty to disable.",
    )
    args = parser.parse_args()

    files = sorted(args.input_dir.glob(args.pattern))
    parsed = {model_label(path): parse_items(path) for path in files}
    model_items = {model: result[0] for model, result in parsed.items()}
    model_stats = {model: {"raw_rows": result[1], "malformed_rows": result[2]} for model, result in parsed.items()}
    models = sorted(model_items)

    by_key: dict[tuple[str, str], dict[str, Item]] = defaultdict(dict)
    for model, items in model_items.items():
        for item in items:
            by_key[item.key][model] = item

    summary_rows = [
        [
            model,
            str(len(items)),
            str(model_stats[model]["raw_rows"]),
            str(model_stats[model]["malformed_rows"]),
        ]
        for model, items in sorted(model_items.items())
    ]
    coverage_rows = []
    price_rows = []
    canonical_category_rows = []
    sides_number_rows = []
    side_choices_rows = []
    split_rows = []

    expected_split = {name.strip() for name in args.split_check.split(",") if name.strip()}
    if expected_split:
        for model, items in sorted(model_items.items()):
            extras = {
                normalize_name(item.dish)
                for item in items
                if normalize_original_category(item.original_category) == "extras"
            }
            missing = sorted(expected_split - extras)
            split_rows.append([model, ", ".join(sorted(expected_split & extras)) or "-", ", ".join(missing) or "-"])

    for key, present in sorted(by_key.items(), key=lambda pair: (pair[0][1], pair[0][0])):
        sample = next(iter(present.values()))
        if len(present) != len(models):
            coverage_rows.append(
                [
                    sample.dish,
                    sample.original_category,
                    ", ".join(sorted(present)),
                    ", ".join(model for model in models if model not in present),
                ]
            )

        prices = {normalize_price(item.price) for item in present.values()}
        if len(prices) > 1:
            price_rows.append([sample.dish, sample.original_category, grouped_values(present, "price", normalize_price)])

        canonical_categories = {normalize_text(item.canonical_category) for item in present.values()}
        if len(canonical_categories) > 1:
            canonical_category_rows.append(
                [sample.dish, sample.original_category, grouped_values(present, "canonical_category", normalize_text)]
            )

        sides_numbers = {normalize_text(item.sides_number) for item in present.values()}
        if len(sides_numbers) > 1:
            sides_number_rows.append(
                [sample.dish, sample.original_category, grouped_values(present, "sides_number", normalize_text)]
            )

        side_choices = {normalize_text(item.side_choices) for item in present.values()}
        if len(side_choices) > 1:
            side_choices_rows.append(
                [sample.dish, sample.original_category, grouped_values(present, "side_choices", normalize_text)]
            )

    lines = [
        "# Canonical Category Menu Output Comparison",
        "",
        f"Source: `{args.source_label}`",
        "",
        "## Summary",
        "",
        table(["Model", "Parsed rows", "Raw non-comment rows", "Malformed rows"], summary_rows),
        "",
        "## Missing Or Extra Rows",
        "",
        table(["Dish", "Original Category", "Present in", "Missing from"], coverage_rows) if coverage_rows else "No coverage differences.",
        "",
        "## Price Disagreements",
        "",
        table(["Dish", "Original Category", "Prices by model"], price_rows) if price_rows else "No price disagreements.",
        "",
        "## Canonical Category Disagreements",
        "",
        table(["Dish", "Original Category", "Canonical categories by model"], canonical_category_rows)
        if canonical_category_rows
        else "No canonical-category disagreements.",
        "",
        "## Sides Number Disagreements",
        "",
        table(["Dish", "Original Category", "Sides numbers by model"], sides_number_rows)
        if sides_number_rows
        else "No sides-number disagreements.",
        "",
        "## Side Choices Disagreements",
        "",
        table(["Dish", "Original Category", "Side choices by model"], side_choices_rows)
        if side_choices_rows
        else "No side-choices disagreements.",
        "",
    ]
    if expected_split:
        lines[8:8] = [
            "## Split Check",
            "",
            table(["Model", "Split rows present", "Missing split rows"], split_rows),
            "",
        ]
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
