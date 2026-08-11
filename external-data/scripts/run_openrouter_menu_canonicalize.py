#!/usr/bin/env python3
"""Normalize extracted menu text into a canonical pipe-delimited item list."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODELS = ROOT / "external-data/derived-untracked/canonical-menu-models.txt"
DEFAULT_INPUT = ROOT / "external-data/menu-scraping/openrouter_vision_half/menu-flyer-1-google__gemini-3.1-flash-lite.md"
DEFAULT_OUTPUT_DIR = ROOT / "external-data/menu-scraping/canonical_openrouter"
DEFAULT_ENV = Path.home() / "Projects/model-labs/.env.local"
DEFAULT_MODELS_METADATA = Path("/tmp/openrouter-models.json")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_TIMEOUT_SECONDS = 90


PROMPT = """You are converting extracted restaurant menu text into a canonical menu item list.

Output only menu items, one item per line, in exactly this pipe-delimited format:

Dish name | Category | Base Price | Description

Rules:
- Do not output an introduction, summary, table header, Markdown table, code fence, or notes.
- Do not output thinking, reasoning, XML-style tags, or hidden-analysis markers.
- Process the entire menu text from beginning to end; do not stop after the first section.
- Every item must have a Base Price.
- Do not output any item with a Base Price of $0 or $0.00. No menu item should have a zero price.
- If a section has a shared price, use that shared price as the Base Price for each item in the section.
- If an item has multiple prices/options, use the lowest real menu price as the Base Price and put the options in the Description.
- Use plain numeric prices with a dollar sign, such as $10 or $10.50.
- Category can be omitted only if there is no category; keep the empty field, like: Dish name |  | $10 | Description.
- Keep descriptions concise but preserve important choices, proteins, side counts, upcharges, and included items.
- Never remove useful information. You may clean up typos, odd phrasing, poor grammar, or excessive wordiness.
- If you are 100% sure a value or phrase is an OCR/source error, you may correct it, but do not guess.
- Do not invent menu items or prices that are not supported by the text.
"""


PROMPT_WITH_SIDES = """You are converting extracted restaurant menu text into a canonical menu item list.

Output only menu items, one item per line, in exactly this pipe-delimited format:

Dish name | Category | Base Price | Sides Number | Side Choices | Description

Rules:
- Do not output an introduction, summary, table header, Markdown table, code fence, or notes.
- Do not output thinking, reasoning, XML-style tags, or hidden-analysis markers.
- Process the entire menu text from beginning to end; do not stop after the first section.
- Every item must have a Base Price.
- If a section has a shared price, use that shared price as the Base Price for each item in the section.
- If an item has multiple prices/options, use the lowest real menu price as the Base Price and put the options in the Description.
- Use plain numeric prices with a dollar sign, such as $10 or $10.50.
- Remove menu numbering or list markers from dish names, such as "1.", "#1", or "12)". Preserve meaningful quantities like "2 tacos" or "one dozen" in the Description.
- Category can be omitted only if there is no category; keep the empty field.
- Sides Number must be a number like 0, 1, or 2. Use 0 when the item does not include sides or the text does not say sides are included.
- Side Choices should contain the available side choices when the source text lists them.
- Do not create separate menu-item rows for included side choices unless the source text gives them standalone prices.
- For day-of-week specials, use the special food/item name as the dish name, use Specials as the category unless a more specific category is present, and include the day or date restrictions in the Description.
- Keep descriptions concise but preserve important choices, proteins, upcharges, included items, and special restrictions.
- Never remove useful information. You may clean up typos, odd phrasing, poor grammar, or excessive wordiness.
- If you are 100% sure a value or phrase is an OCR/source error, you may correct it, but do not guess.
- Do not invent menu items or prices that are not supported by the text.
"""


PROMPT_WITH_CANONICAL_CATEGORY = """You are converting extracted restaurant menu text into a canonical menu item list.

Output only menu items as a standard Markdown table with this exact header row:

| Dish name | Original Category | Canonical Category | Base Price | Sides Number | Side Choices | Description |
| --- | --- | --- | --- | --- | --- | --- |

Rules:
- Do not output an introduction, summary, code fence, or notes.
- Do not output thinking, reasoning, XML-style tags, or hidden-analysis markers.
- Output the Markdown table header and separator row exactly once, followed by one item row per menu item.
- Every output item row must have exactly 7 columns.
- Process the entire menu text from beginning to end; do not stop after the first section.
- Input may be plain text, OCR text, or compact HTML. If HTML is present, use the visible text and structural class names to identify sections, item names, descriptions, and prices.
- Output one row for every source menu item, except split combined priced option rows into separate rows as instructed below.
- Every item must have a Base Price.
- If a section has a shared price, use that shared price as the Base Price for each item in the section.
- If an item has multiple sizes or prices, use the lowest real menu price as the Base Price and put the size/price options in the Description.
- Use plain numeric prices with a dollar sign, such as $10 or $10.50.
- Remove menu numbering or list markers from dish names, such as "1.", "#1", or "12)". Preserve meaningful quantities like "2 tacos" or "one dozen" in the Description.
- Do not add size information to the dish name unless it is already present in the original.
- Look for spice or heat level information, which may be indicated by stars, asterisks, emoji, icons, or words like mild, hot, spicy, or hottest. Put spice or heat level information in the Description.
- Remove decorative spice markers from dish names when they only indicate heat level; preserve their meaning in the Description.
- Original Category must preserve the restaurant's menu section name as closely as possible.
- Canonical Category should be a normalized broad category useful across restaurants. Prefer common broad values like Entree, Appetizer, Side, Dessert, Family Meal, Special, Drink, Add-on, A-la-carte, or Other, and use more specific food-type categories like Taco, Burrito, Bowl, Pizza, Sandwich, Salad, or Soup when that is more useful.
- Use the item's price as one weak signal for Canonical Category. Sides are generally cheaper than appetizers, appetizers are generally cheaper than entrees, and entrees are generally cheaper than meals, dinners, combos, or family packs. Do not rely on price alone when the item name or section clearly says otherwise.
- Keep both category fields even when they are similar.
- Sides Number must be a number like 0, 1, or 2. Use 0 when the item does not include sides or the text does not say sides are included.
- Side Choices should contain available side choices only when the item includes sides and the source text lists the choices.
- Do not create separate menu-item rows for included side choices unless the source text gives them standalone prices.
- For day-of-week specials, use the special food/item name as the dish name, preserve the source section name as Original Category, use Special as Canonical Category unless another category is clearly better, and include the weekday, per-item wording like "ea.", limits, and restrictions in the Description.
- Each output row must represent one orderable item, possibly with modifications, sizes, or options. A dish name should rarely be a list of alternatives.
- If a source line contains item names joined by a case-insensitive word like "or"/"OR", decide whether it is one item with options or multiple orderable items printed on one line for convenience.
- Do not split a line when the words describe alternate names, modifiers, protein choices, sauce choices, included components, or sizes of one item; preserve those details in the Description instead.
- Keep descriptions concise but preserve all useful choices, proteins, sizes, alternate prices, upcharges, included items, limits, restrictions, and special notes.
- Never remove useful information. You may clean up typos, odd phrasing, poor grammar, or excessive wordiness.
- If you are 100% sure a value or phrase is an OCR/source error, you may correct it, but do not guess.
- Do not invent menu items or prices that are not supported by the text.
- Keep size differences in the description if the menu has it that way.
"""


def load_env_key(path: Path) -> str:
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key == "OPENROUTER_API_KEY":
            return value.strip().strip('"').strip("'")
    raise RuntimeError(f"OPENROUTER_API_KEY not found in {path}")


def model_slug(model: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", model.replace("/", "__")).strip("-")


def call_model(
    model: str,
    menu_text: str,
    api_key: str,
    timeout: int,
    prompt: str,
    max_tokens: int,
    temperature: float,
    reasoning_effort: str | None,
) -> dict:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Menu text:\n\n{menu_text}"},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if reasoning_effort:
        payload["include_reasoning"] = True
        payload["reasoning"] = {"effort": reasoning_effort}
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OPENROUTER_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/tbsisan/restaurant-menu-search",
            "X-Title": "restaurant-menu-search menu canonicalization spike",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def response_text(response: dict) -> str:
    choice = (response.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    content = message.get("content") or ""
    if isinstance(content, list):
        return "\n\n".join(str(item.get("text", "")) for item in content if isinstance(item, dict)).strip()
    return str(content).strip()


def output_text(model: str, source: Path, response: dict, elapsed_seconds: float | None = None) -> str:
    usage = response.get("usage") or {}
    elapsed_line = f"<!-- elapsed_seconds: {elapsed_seconds:.3f} -->\n" if elapsed_seconds is not None else ""
    return (
        f"<!-- model: {model} -->\n"
        f"<!-- source: {source} -->\n"
        f"{elapsed_line}"
        f"<!-- usage: {json.dumps(usage, sort_keys=True)} -->\n\n"
        f"{response_text(response)}\n"
    )


def load_reasoning_efforts(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    efforts = {}
    priority = ["max", "xhigh", "high", "medium", "low", "minimal"]
    for model in json.loads(path.read_text(encoding="utf-8")).get("data", []):
        reasoning = model.get("reasoning") or {}
        supported = reasoning.get("supported_efforts") or []
        for effort in priority:
            if effort in supported:
                efforts[model["id"]] = effort
                break
    return efforts


def run_one_model(
    model: str,
    menu_text: str,
    api_key: str,
    prompt: str,
    source: Path,
    output_dir: Path,
    output_prefix: str,
    timeout: int,
    max_tokens: int,
    temperature: float,
    reasoning_effort: str | None,
) -> str:
    slug = model_slug(model)
    output = output_dir / f"{output_prefix}-{slug}.txt"
    error_output = output_dir / f"{output_prefix}-{slug}.error.json"
    started_at = time.monotonic()
    try:
        response = call_model(model, menu_text, api_key, timeout, prompt, max_tokens, temperature, reasoning_effort)
    except urllib.error.HTTPError as exc:
        elapsed = time.monotonic() - started_at
        error_body = exc.read().decode("utf-8", errors="replace")
        error_output.write_text(
            json.dumps(
                {
                    "model": model,
                    "elapsed_seconds": round(elapsed, 3),
                    "status": exc.code,
                    "reason": exc.reason,
                    "body": error_body,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return f"  error {exc.code} after {elapsed:.1f}s; wrote {error_output.name}"
    except Exception as exc:
        elapsed = time.monotonic() - started_at
        error_output.write_text(
            json.dumps(
                {
                    "model": model,
                    "elapsed_seconds": round(elapsed, 3),
                    "error": f"{type(exc).__name__}: {exc}",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return f"  error after {elapsed:.1f}s; wrote {error_output.name}"

    elapsed = time.monotonic() - started_at
    output.write_text(output_text(model, source, response, elapsed), encoding="utf-8")
    return f"  wrote {output.name} after {elapsed:.1f}s"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", type=Path, default=DEFAULT_MODELS)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--output-prefix", default="canonical-menu-flyer-1-gemini-flash-lite")
    parser.add_argument("--schema", choices=["basic", "sides", "canonical-category"], default="basic")
    parser.add_argument("--env", type=Path, default=DEFAULT_ENV)
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="OpenRouter request timeout in seconds for each model call.",
    )
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--max-tokens", type=int, default=6000)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--concurrency", type=int, default=1, help="Number of model calls to run in parallel.")
    parser.add_argument(
        "--reasoning-effort",
        default=None,
        help="Reasoning effort to request for every model, or auto-max to use each model's highest supported effort.",
    )
    parser.add_argument("--models-metadata", type=Path, default=DEFAULT_MODELS_METADATA)
    args = parser.parse_args()

    api_key = load_env_key(args.env)
    if args.schema == "sides":
        prompt = PROMPT_WITH_SIDES
    elif args.schema == "canonical-category":
        prompt = PROMPT_WITH_CANONICAL_CATEGORY
    else:
        prompt = PROMPT
    menu_text = args.input.read_text(encoding="utf-8")
    models = [line.strip() for line in args.models.read_text().splitlines() if line.strip() and not line.startswith("#")]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    reasoning_efforts = load_reasoning_efforts(args.models_metadata) if args.reasoning_effort == "auto-max" else {}

    concurrency = max(1, args.concurrency)
    print(f"Running {len(models)} model calls with concurrency={concurrency}", flush=True)
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {}
        for model in models:
            reasoning_effort = reasoning_efforts.get(model) if args.reasoning_effort == "auto-max" else args.reasoning_effort
            reasoning_label = f", reasoning={reasoning_effort}" if reasoning_effort else ""
            print(f"Calling {model} (timeout {args.timeout}s{reasoning_label})", flush=True)
            future = executor.submit(
                run_one_model,
                model,
                menu_text,
                api_key,
                prompt,
                args.input,
                args.output_dir,
                args.output_prefix,
                args.timeout,
                args.max_tokens,
                args.temperature,
                reasoning_effort,
            )
            futures[future] = model
            if args.delay > 0:
                time.sleep(args.delay)

        for future in as_completed(futures):
            model = futures[future]
            try:
                message = future.result()
            except Exception as exc:
                message = f"  unexpected worker error for {model}: {type(exc).__name__}: {exc}"
            print(f"{model}\n{message}", flush=True)


if __name__ == "__main__":
    main()
