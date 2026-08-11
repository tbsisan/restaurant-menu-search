#!/usr/bin/env python3
"""Evaluate plain-text Google results for restaurant-data link usefulness."""

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
DEFAULT_ENV = Path.home() / "Projects/model-labs/.env.local"
DEFAULT_MODELS = ROOT / "external-data/derived-untracked/google-results-link-eval-models.txt"
DEFAULT_OUTPUT_DIR = ROOT / "external-data/google-results-link-eval"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_TIMEOUT_SECONDS = 90


PROMPT = """You evaluate Google search results utility for a restaurant-data scraping project.

The user will provide plain text from one page of Google results. For each actual search result, identify:

- URL
- what_the_result_is: short description of the site/page
- useful_data_types: list any likely useful restaurant data types, such as:
  social_media_page, menu_site, restaurants_own_website, local_news_or_blog,
  awards_or_best_of, industry_zine, event_participated_in, other_restaurant_context
- whether it may be useful: one concise sentence
- usefulness: high, medium, low, or none

Rules:
- Output Markdown only.
- Use a Markdown table with these exact columns:
  URL | What the result is | Useful data types | Usefulness | Why it may be useful
- After the table, add a short "Summary" section with counts for high, medium, low, and none.
- Dining rewards sites/programs (SkyMiles Dining, Hilton/Marriott dining, Upside Fuel Rewards, T-mobile Dining Rewards, etc.) are useful restaurant-data sources. They often share Rewards Network data, so rate the first distinct listing high if restaurant-specific; rate duplicates low.
- Restaurant-specific social media pages and specific post/status links are likely useful for profile IDs, posts, photos, specials, events, popularity signals, and current restaurant context.
- Smaller/unknown menu sites like Zmenu often republish info from other sources, so rate them below primary sources unless they clearly add unique restaurant-specific details.
- The input may contain up to 3 pages of Google results; lower-ranked listings are less likely to be useful.
- Do not include ads, navigation links, "People also ask", query suggestions, or Google UI controls unless they point to a real external page.
- If a result is ambiguous, include it with usefulness "low" and explain why.
- Do not browse the web. Judge only from the provided Google result text.
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


def response_text(response: dict) -> str:
    choice = (response.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    content = message.get("content") or ""
    if isinstance(content, list):
        return "\n\n".join(str(item.get("text", "")) for item in content if isinstance(item, dict)).strip()
    return str(content).strip()


def call_model(
    model: str,
    results_text: str,
    api_key: str,
    timeout: int,
    max_tokens: int,
    temperature: float,
) -> dict:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": f"Google results text:\n\n{results_text}"},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OPENROUTER_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/tbsisan/restaurant-menu-search",
            "X-Title": "restaurant-menu-search Google result link evaluation",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def output_markdown(model: str, source: Path, response: dict, elapsed_seconds: float) -> str:
    usage = response.get("usage") or {}
    return (
        f"<!-- model: {model} -->\n"
        f"<!-- source: {source} -->\n"
        f"<!-- elapsed_seconds: {elapsed_seconds:.3f} -->\n"
        f"<!-- usage: {json.dumps(usage, sort_keys=True)} -->\n\n"
        f"{response_text(response)}\n"
    )


def parse_json_response(text: str) -> object:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return json.loads(stripped)


def run_one_model(
    model: str,
    source: Path,
    results_text: str,
    api_key: str,
    output_dir: Path,
    output_prefix: str,
    timeout: int,
    max_tokens: int,
    temperature: float,
) -> dict:
    slug = model_slug(model)
    md_output = output_dir / f"{output_prefix}-{slug}.md"
    error_output = output_dir / f"{output_prefix}-{slug}.error.json"
    started_at = time.monotonic()

    try:
        response = call_model(model, results_text, api_key, timeout, max_tokens, temperature)
        elapsed = time.monotonic() - started_at
        md_output.write_text(output_markdown(model, source, response, elapsed), encoding="utf-8")
        return {"model": model, "ok": True, "elapsed": elapsed, "output": str(md_output)}
    except urllib.error.HTTPError as exc:
        elapsed = time.monotonic() - started_at
        error_output.write_text(
            json.dumps(
                {
                    "model": model,
                    "elapsed_seconds": round(elapsed, 3),
                    "status": exc.code,
                    "reason": exc.reason,
                    "body": exc.read().decode("utf-8", errors="replace"),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return {"model": model, "ok": False, "elapsed": elapsed, "output": str(error_output)}
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
        return {"model": model, "ok": False, "elapsed": elapsed, "output": str(error_output)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True, help="Plain-text Google results file")
    parser.add_argument("--models", type=Path, default=DEFAULT_MODELS)
    parser.add_argument("--model", action="append", help="Model id; can be repeated. Overrides --models.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--output-prefix", default="google-results-link-eval")
    parser.add_argument("--flat-output", action="store_true", help="Write files directly to --output-dir instead of a run subdirectory.")
    parser.add_argument("--env", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--max-tokens", type=int, default=3000)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--concurrency", type=int, default=4)
    args = parser.parse_args()

    if args.concurrency < 1:
        raise ValueError("--concurrency must be at least 1")

    api_key = load_env_key(args.env)
    results_text = args.input.read_text(encoding="utf-8")
    if args.model:
        models = args.model
    else:
        models = [
            line.strip()
            for line in args.models.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]
    if not args.flat_output:
        args.output_dir = args.output_dir / args.output_prefix
    args.output_dir.mkdir(parents=True, exist_ok=True)
    file_prefix = args.output_prefix if args.flat_output else "run"

    run_manifest = {
        "input": str(args.input),
        "models": models,
        "prompt": PROMPT,
        "started_at_unix": time.time(),
    }
    (args.output_dir / f"{file_prefix}-manifest.json").write_text(
        json.dumps(run_manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Evaluating {args.input} with {len(models)} model(s)", flush=True)
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = {
            executor.submit(
                run_one_model,
                model,
                args.input,
                results_text,
                api_key,
                args.output_dir,
                file_prefix,
                args.timeout,
                args.max_tokens,
                args.temperature,
            ): model
            for model in models
        }
        for future in as_completed(futures):
            result = future.result()
            status = "ok" if result["ok"] else "failed"
            print(
                f"{result['model']}: {status} after {result['elapsed']:.1f}s; {result['output']}",
                flush=True,
            )


if __name__ == "__main__":
    main()
