#!/usr/bin/env python3
"""Compare sides-aware canonical menu outputs from multiple models."""

from __future__ import annotations

import argparse
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_DIR = ROOT / "external-data/menu-scraping/canonical_openrouter"
DEFAULT_PATTERN = "canonical-sides-menu-flyer-1-gemini-flash-lite-*.txt"
DEFAULT_OUTPUT = DEFAULT_INPUT_DIR / "canonical-sides-menu-flyer-1-gemini-flash-lite-comparison.md"


@dataclass(frozen=True)
class Item:
    dish: str
    category: str
    price: str
    sides_number: str
    side_choices: str
    description: str

    @property
    def key(self) -> tuple[str, str]:
        return normalize_name(self.dish), normalize_category(self.category)


def normalize_name(value: str) -> str:
    value = value.strip().lower().replace("&", "and")
    value = re.sub(r"[^a-z0-9/ ]+", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.replace("enchiladas/enchiladas suizas", "enchiladas")


def normalize_category(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9 ]+", "", value)
    return re.sub(r"\s+", " ", value)


def normalize_price(value: str) -> str:
    match = re.search(r"\$?\s*(\d+(?:\.\d{1,2})?)", value.strip())
    if not match:
        return value.strip()
    return f"${float(match.group(1)):.2f}"


def normalize_sides_number(value: str) -> str:
    match = re.search(r"\d+", value)
    return match.group(0) if match else value.strip()


def normalize_side_choices(value: str) -> str:
    choices = []
    for part in re.split(r"[,;/]|\band\b", value.lower()):
        part = re.sub(r"[^a-z0-9 ]+", "", part).strip()
        part = re.sub(r"\s+", " ", part)
        if part:
            choices.append(part)
    return ", ".join(sorted(set(choices)))


def model_label(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"<!-- model: (.*?) -->", text)
    if match:
        return match.group(1)
    return path.stem


def parse_items(path: Path) -> list[Item]:
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("<!--"):
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) == 6:
            items.append(Item(*parts))
    return items


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
    args = parser.parse_args()

    files = sorted(args.input_dir.glob(args.pattern))
    model_items = {model_label(path): parse_items(path) for path in files}
    model_items = {model: items for model, items in model_items.items() if items}
    models = sorted(model_items)

    by_key: dict[tuple[str, str], dict[str, Item]] = defaultdict(dict)
    for model, items in model_items.items():
        for item in items:
            by_key[item.key][model] = item

    summary_rows = [[model, str(len(items))] for model, items in sorted(model_items.items())]

    coverage_rows = []
    price_rows = []
    sides_number_rows = []
    side_choices_rows = []
    name_rows = []
    for key, present in sorted(by_key.items(), key=lambda pair: (pair[0][1], pair[0][0])):
        sample = next(iter(present.values()))
        if len(present) != len(models):
            coverage_rows.append(
                [
                    sample.dish,
                    sample.category,
                    ", ".join(sorted(present)),
                    ", ".join(model for model in models if model not in present),
                ]
            )

        prices = {normalize_price(item.price) for item in present.values()}
        if len(prices) > 1:
            price_rows.append([sample.dish, sample.category, grouped_values(present, "price", normalize_price)])

        sides_numbers = {normalize_sides_number(item.sides_number) for item in present.values()}
        if len(sides_numbers) > 1:
            sides_number_rows.append([sample.dish, sample.category, grouped_values(present, "sides_number", normalize_sides_number)])

        side_choices = {normalize_side_choices(item.side_choices) for item in present.values()}
        if len(side_choices) > 1:
            side_choices_rows.append([sample.dish, sample.category, grouped_values(present, "side_choices", normalize_side_choices)])

        names = defaultdict(list)
        for model, item in present.items():
            names[item.dish].append(model)
        if len(names) > 1:
            name_rows.append(
                [
                    sample.category,
                    "; ".join(f"{name}: {', '.join(sorted(model_names))}" for name, model_names in sorted(names.items())),
                ]
            )

    lines = [
        "# Sides-Aware Canonical Menu Output Comparison",
        "",
        "Source OCR: `menu-flyer-1-google__gemini-3.1-flash-lite.md`",
        "",
        "## Summary",
        "",
        table(["Model", "Parsed rows"], summary_rows),
        "",
        "## Missing Or Extra Rows",
        "",
        table(["Dish", "Category", "Present in", "Missing from"], coverage_rows) if coverage_rows else "No coverage differences.",
        "",
        "## Price Disagreements",
        "",
        table(["Dish", "Category", "Prices by model"], price_rows) if price_rows else "No price disagreements.",
        "",
        "## Sides Number Disagreements",
        "",
        table(["Dish", "Category", "Sides number by model"], sides_number_rows) if sides_number_rows else "No sides-number disagreements.",
        "",
        "## Side Choices Disagreements",
        "",
        table(["Dish", "Category", "Side choices by model"], side_choices_rows) if side_choices_rows else "No side-choice disagreements after normalization.",
        "",
        "## Naming Differences",
        "",
        table(["Category", "Names by model"], name_rows) if name_rows else "No naming differences after normalization.",
        "",
    ]
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
