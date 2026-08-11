#!/usr/bin/env python3
"""Compare canonicalized menu outputs from multiple models."""

from __future__ import annotations

import argparse
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_DIR = ROOT / "external-data/menu-scraping/canonical_openrouter"
DEFAULT_OUTPUT = DEFAULT_INPUT_DIR / "canonical-menu-flyer-1-gemini-flash-lite-comparison.md"
DEFAULT_PATTERN = "canonical-menu-flyer-1-gemini-flash-lite-*.txt"


@dataclass(frozen=True)
class Item:
    dish: str
    category: str
    price: str
    description: str

    @property
    def key(self) -> tuple[str, str]:
        name = normalize_name(self.dish)
        category = normalize_category(self.category)
        if name in SIDE_DISH_NAMES:
            category = "sides"
        return name, category


SIDE_DISH_NAMES = {"refried beans", "papas", "spanish rice", "cilantro lime rice", "charro beans"}


def normalize_name(value: str) -> str:
    value = value.strip().lower()
    value = value.replace("&", "and")
    value = re.sub(r"[^a-z0-9/ ]+", "", value)
    value = re.sub(r"\s+", " ", value)
    value = value.replace("enchiladas/enchiladas suizas", "enchiladas")
    return value


def normalize_category(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9 ]+", "", value)
    value = re.sub(r"\s+", " ", value)
    return value


def normalize_price(value: str) -> str:
    value = value.strip()
    match = re.search(r"\$?\s*(\d+(?:\.\d{1,2})?)", value)
    if not match:
        return value
    amount = float(match.group(1))
    return f"${amount:.2f}"


def has_valid_price(value: str) -> bool:
    return bool(re.search(r"\$?\s*\d+(?:\.\d{1,2})?", value.strip()))


def model_label(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"<!-- model: (.*?) -->", text)
    if match:
        return match.group(1)
    prefix = "canonical-menu-flyer-1-gemini-flash-lite-"
    return path.stem.removeprefix(prefix)


def parse_items(path: Path) -> list[Item]:
    items: list[Item] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("<!--"):
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) != 4:
            continue
        items.append(Item(*parts))
    return items


def table(headers: list[str], rows: list[list[str]]) -> str:
    out = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    out.extend("| " + " | ".join(escape_cell(cell) for cell in row) + " |" for row in rows)
    return "\n".join(out)


def escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", "<br>")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--pattern", default=DEFAULT_PATTERN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    files = sorted(args.input_dir.glob(args.pattern))
    model_items = {model_label(path): parse_items(path) for path in files}
    by_key: dict[tuple[str, str], dict[str, Item]] = defaultdict(dict)
    for model, items in model_items.items():
        for item in items:
            by_key[item.key][model] = item

    models = sorted(model_items)
    rows = []
    for model in models:
        items = model_items[model]
        unsupported_sides = [
            item.dish
            for item in items
            if normalize_name(item.dish) in SIDE_DISH_NAMES
        ]
        invalid_prices = [item.dish for item in items if not has_valid_price(item.price) or normalize_price(item.price) == "$0.00"]
        rows.append([model, str(len(items)), ", ".join(unsupported_sides) or "-", ", ".join(invalid_prices) or "-"])

    coverage_rows = []
    for key, present in sorted(by_key.items(), key=lambda pair: (pair[0][1], pair[0][0])):
        if len(present) == len(models):
            continue
        sample = next(iter(present.values()))
        missing = [model for model in models if model not in present]
        coverage_rows.append([sample.dish, sample.category, ", ".join(sorted(present)), ", ".join(missing)])

    price_rows = []
    for key, present in sorted(by_key.items(), key=lambda pair: (pair[0][1], pair[0][0])):
        prices = defaultdict(list)
        for model, item in present.items():
            prices[normalize_price(item.price)].append(model)
        if len(prices) <= 1:
            continue
        sample = next(iter(present.values()))
        price_rows.append(
            [
                sample.dish,
                sample.category,
                "; ".join(f"{price}: {', '.join(sorted(models_for_price))}" for price, models_for_price in sorted(prices.items())),
            ]
        )

    name_rows = []
    for key, present in sorted(by_key.items(), key=lambda pair: (pair[0][1], pair[0][0])):
        names = defaultdict(list)
        for model, item in present.items():
            names[item.dish].append(model)
        if len(names) <= 1:
            continue
        name_rows.append(
            [
                next(iter(present.values())).category,
                "; ".join(f"{name}: {', '.join(sorted(models_for_name))}" for name, models_for_name in sorted(names.items())),
            ]
        )

    lines = [
        "# Canonical Menu Output Comparison",
        "",
        "Source OCR: `menu-flyer-1-google__gemini-3.1-flash-lite.md`",
        "",
        "## Summary",
        "",
        table(["Model", "Parsed rows", "Unsupported side rows", "Invalid/missing prices"], rows),
        "",
        "## Missing Or Extra Rows",
        "",
        table(["Dish", "Category", "Present in", "Missing from"], coverage_rows) if coverage_rows else "No coverage differences.",
        "",
        "## Price Disagreements",
        "",
        table(["Dish", "Category", "Prices by model"], price_rows) if price_rows else "No price disagreements among aligned rows.",
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
