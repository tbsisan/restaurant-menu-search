#!/usr/bin/env python3
"""Batch-evaluate Google result usefulness across cheap OpenRouter models."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import math
import re
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV = Path.home() / "Projects/model-labs/.env.local"
DEFAULT_CATALOG = ROOT.parent / "model-labs/external-data/derived/model-catalog/generated.json"
DEFAULT_INPUT = ROOT / "external-data/google-results/camino-real/camino-real.json"
DEFAULT_OUTPUT_DIR = ROOT / "external-data/google-results-link-eval/batch"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
SCORE_BY_USEFULNESS = {"none": 0, "low": 1, "medium": 2, "high": 3}
USEFULNESS_BY_SCORE = {value: key for key, value in SCORE_BY_USEFULNESS.items()}


PROMPT = """You evaluate Google search result utility for a restaurant-data scraping project.

For each numbered Google result, decide whether the result may contain useful restaurant data.
Useful data includes restaurant reviews, likes/follower signals, social media pages, menu info,
online ordering/menu pages, local news/blog mentions, awards, events, or general information
about the restaurant.

Return JSON only, with this exact shape:
{
  "results": [
    {
      "index": 1,
      "url": "https://example.com/",
      "what_the_result_is": "short description",
      "useful_data_types": ["restaurants_own_website"],
      "usefulness": "high",
      "why": "one concise sentence"
    }
  ]
}

Rules:
- Include every numbered result exactly once.
- Use usefulness exactly as one of: high, medium, low, none.
- Dining rewards sites/programs (SkyMiles Dining, Hilton/Marriott dining, Upside Fuel Rewards, T-mobile Dining Rewards, etc.) are useful restaurant-data sources. They often share Rewards Network data, so rate the first distinct listing high if restaurant-specific; rate duplicates low.
- Restaurant-specific social media pages and specific post/status links are likely useful for profile IDs, posts, photos, specials, events, popularity signals, and current restaurant context.
- Smaller/unknown menu sites like Zmenu often republish info from other sources, so rate them below primary sources unless they clearly add unique restaurant-specific details.
- The input may contain up to 3 pages of Google results; lower-ranked listings are less likely to be useful.
- Judge only from the supplied Google result text. Do not browse.
- If ambiguous, choose low and explain why.
- Do not include ads, navigation links, People also ask, query suggestions, or Google UI controls.
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
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("text"):
                parts.append(str(item["text"]))
        return "\n\n".join(parts).strip()
    return str(content).strip()


def parse_jsonish(text: str) -> dict:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    if not stripped.startswith("{"):
        match = re.search(r"\{.*\}", stripped, flags=re.S)
        if match:
            stripped = match.group(0)
    return json.loads(stripped)


def load_models(catalog_path: Path, max_input_cost: float) -> list[dict]:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    models = []
    for model in catalog.get("models", []):
        cost = model.get("pricePerMillionInputTokens")
        if cost is None or cost > max_input_cost:
            continue
        if model.get("provider") != "openrouter":
            continue
        if "text" not in model.get("inputModalities", []):
            continue
        models.append(model)
    return models


def load_google_results(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    results = []
    running_index = 1
    for page in data.get("pages", []):
        for result in page.get("results", []):
            results.append(
                {
                    "index": running_index,
                    "page": page.get("page"),
                    "page_index": result.get("index"),
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "text": result.get("text", ""),
                }
            )
            running_index += 1
    if not results and data.get("results"):
        for result in data["results"]:
            result = dict(result)
            result["index"] = running_index
            results.append(result)
            running_index += 1
    return results


def results_payload(results: list[dict]) -> str:
    lines = []
    for result in results:
        lines.append(
            "\n".join(
                [
                    f"Result {result['index']}",
                    f"Title: {result.get('title', '')}",
                    f"URL: {result.get('url', '')}",
                    f"Text: {result.get('text', '')}",
                ]
            )
        )
    return "\n\n".join(lines)


def call_model(model_id: str, result_text: str, api_key: str, max_tokens: int, temperature: float, timeout: int) -> dict:
    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": f"Google results:\n\n{result_text}"},
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
            "X-Title": "restaurant-menu-search batch Google result evaluation",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def normalize_parsed(parsed: dict, canonical_results: list[dict]) -> list[dict]:
    by_index = {result["index"]: result for result in canonical_results}
    normalized = []
    seen_indexes = set()
    for item in parsed.get("results", []):
        try:
            index = int(item.get("index"))
        except (TypeError, ValueError):
            continue
        if index not in by_index:
            continue
        if index in seen_indexes:
            continue
        seen_indexes.add(index)
        usefulness = str(item.get("usefulness", "")).strip().lower()
        if usefulness not in SCORE_BY_USEFULNESS:
            continue
        canonical = by_index[index]
        normalized.append(
            {
                "index": index,
                "url": canonical["url"],
                "title": canonical.get("title", ""),
                "what_the_result_is": str(item.get("what_the_result_is", "")).strip(),
                "useful_data_types": item.get("useful_data_types") if isinstance(item.get("useful_data_types"), list) else [],
                "usefulness": usefulness,
                "score": SCORE_BY_USEFULNESS[usefulness],
                "why": str(item.get("why", "")).strip(),
            }
        )
    return normalized


def run_one(
    model: dict,
    result_text: str,
    canonical_results: list[dict],
    api_key: str,
    output_dir: Path,
    output_prefix: str,
    requested_max_tokens: int,
    temperature: float,
    timeout: int,
) -> dict:
    model_id = model["modelId"]
    slug = model_slug(model_id)
    max_completion = model.get("maxCompletionTokens")
    effective_max_tokens = min(requested_max_tokens, max_completion) if max_completion else requested_max_tokens
    started = time.monotonic()
    base_name = f"{output_prefix}-{slug}"
    api_output = output_dir / f"{base_name}.api.json"
    response_output = output_dir / f"{base_name}.response.md"
    parsed_output = output_dir / f"{base_name}.parsed.json"
    error_output = output_dir / f"{base_name}.error.json"
    try:
        response = call_model(model_id, result_text, api_key, effective_max_tokens, temperature, timeout)
        elapsed = time.monotonic() - started
        text = response_text(response)
        api_output.write_text(json.dumps(response, indent=2) + "\n", encoding="utf-8")
        response_output.write_text(
            f"<!-- model: {model_id} -->\n"
            f"<!-- elapsed_seconds: {elapsed:.3f} -->\n"
            f"<!-- requested_max_tokens: {requested_max_tokens} -->\n"
            f"<!-- effective_max_tokens: {effective_max_tokens} -->\n"
            f"<!-- usage: {json.dumps(response.get('usage') or {}, sort_keys=True)} -->\n\n"
            f"{text}\n",
            encoding="utf-8",
        )
        parsed = parse_jsonish(text)
        normalized = normalize_parsed(parsed, canonical_results)
        parsed_payload = {
            "model": model_id,
            "elapsed_seconds": round(elapsed, 3),
            "requested_max_tokens": requested_max_tokens,
            "effective_max_tokens": effective_max_tokens,
            "usage": response.get("usage") or {},
            "results": normalized,
        }
        parsed_output.write_text(json.dumps(parsed_payload, indent=2) + "\n", encoding="utf-8")
        return {
            "model": model_id,
            "ok": True,
            "parsed_count": len(normalized),
            "elapsed": elapsed,
            "output": str(response_output),
            "parsed": parsed_payload,
        }
    except urllib.error.HTTPError as exc:
        elapsed = time.monotonic() - started
        error = {
            "model": model_id,
            "elapsed_seconds": round(elapsed, 3),
            "status": exc.code,
            "reason": exc.reason,
            "body": exc.read().decode("utf-8", errors="replace"),
        }
        error_output.write_text(json.dumps(error, indent=2) + "\n", encoding="utf-8")
        return {"model": model_id, "ok": False, "elapsed": elapsed, "output": str(error_output)}
    except Exception as exc:
        elapsed = time.monotonic() - started
        error = {"model": model_id, "elapsed_seconds": round(elapsed, 3), "error": f"{type(exc).__name__}: {exc}"}
        error_output.write_text(json.dumps(error, indent=2) + "\n", encoding="utf-8")
        return {"model": model_id, "ok": False, "elapsed": elapsed, "output": str(error_output)}


def confidence_from_variance(scores: list[int]) -> str:
    if len(scores) < 2:
        return "low"
    variance = statistics.pvariance(scores)
    if variance <= 0.25:
        return "high"
    if variance <= 0.75:
        return "medium"
    return "low"


def aggregate(canonical_results: list[dict], model_results: list[dict]) -> dict:
    by_index: dict[int, list[dict]] = {result["index"]: [] for result in canonical_results}
    seen = set()
    for model_result in model_results:
        if not model_result.get("ok"):
            continue
        model_id = model_result["model"]
        for item in model_result["parsed"]["results"]:
            vote_key = (model_id, item["index"])
            if vote_key in seen:
                continue
            seen.add(vote_key)
            item = dict(item)
            item["model"] = model_id
            by_index[item["index"]].append(item)

    rows = []
    for canonical in canonical_results:
        judgments = by_index[canonical["index"]]
        scores = [item["score"] for item in judgments]
        if scores:
            avg = sum(scores) / len(scores)
            variance = statistics.pvariance(scores) if len(scores) > 1 else 0.0
            rounded = int(round(avg))
            rounded = max(0, min(3, rounded))
            label = USEFULNESS_BY_SCORE[rounded]
        else:
            avg = None
            variance = None
            label = "none"
        counts = {key: 0 for key in ["high", "medium", "low", "none"]}
        for item in judgments:
            counts[item["usefulness"]] += 1
        rows.append(
            {
                "index": canonical["index"],
                "title": canonical.get("title", ""),
                "url": canonical.get("url", ""),
                "avg_score": round(avg, 3) if avg is not None else None,
                "average_usefulness": label,
                "variance": round(variance, 3) if variance is not None else None,
                "confidence": confidence_from_variance(scores),
                "judgment_count": len(judgments),
                "counts": counts,
            }
        )
    return {"results": rows}


def report_markdown(summary: dict, output_json: Path) -> str:
    lines = [
        f"# Google Result Batch Evaluation",
        "",
        f"- Models attempted: {summary['models_attempted']}",
        f"- Models succeeded: {summary['models_succeeded']}",
        f"- Models failed: {summary['models_failed']}",
        f"- Max input cost filter: <= ${summary['max_input_cost']:.2f} per million input tokens",
        f"- Requested max tokens: {summary['requested_max_tokens']}",
        f"- Aggregate JSON: `{output_json}`",
        "",
        "| # | Avg | Confidence | Votes high/med/low/none | Title | URL |",
        "|---:|---:|---|---:|---|---|",
    ]
    for row in summary["aggregate"]["results"]:
        counts = row["counts"]
        votes = f"{counts['high']}/{counts['medium']}/{counts['low']}/{counts['none']}"
        avg = "" if row["avg_score"] is None else f"{row['avg_score']:.2f}"
        lines.append(
            "| {index} | {avg} {label} | {confidence} | {votes} | {title} | {url} |".format(
                index=row["index"],
                avg=avg,
                label=row["average_usefulness"],
                confidence=row["confidence"],
                votes=votes,
                title=str(row["title"]).replace("|", "\\|"),
                url=str(row["url"]).replace("|", "\\|"),
            )
        )
    lines.append("")
    lines.append("Score key: none=0, low=1, medium=2, high=3.")
    return "\n".join(lines) + "\n"


def load_completed_runs_from_files(models: list[dict], output_dir: Path, output_prefix: str) -> list[dict]:
    completed = []
    for model in models:
        model_id = model["modelId"]
        slug = model_slug(model_id)
        base_name = f"{output_prefix}-{slug}"
        parsed_path = output_dir / f"{base_name}.parsed.json"
        error_path = output_dir / f"{base_name}.error.json"
        if parsed_path.exists():
            parsed = json.loads(parsed_path.read_text(encoding="utf-8"))
            completed.append(
                {
                    "model": model_id,
                    "ok": True,
                    "elapsed": parsed.get("elapsed_seconds", 0),
                    "output": str(output_dir / f"{base_name}.response.md"),
                    "parsed_count": len(parsed.get("results", [])),
                    "parsed": parsed,
                }
            )
        elif error_path.exists():
            error = json.loads(error_path.read_text(encoding="utf-8"))
            completed.append(
                {
                    "model": model_id,
                    "ok": False,
                    "elapsed": error.get("elapsed_seconds", 0),
                    "output": str(error_path),
                    "parsed_count": None,
                }
            )
        else:
            completed.append(
                {
                    "model": model_id,
                    "ok": False,
                    "elapsed": 0,
                    "output": str(error_path),
                    "parsed_count": None,
                }
            )
    return completed


def write_aggregate_report(
    args: argparse.Namespace,
    canonical_results: list[dict],
    models: list[dict],
    completed: list[dict],
) -> tuple[Path, Path]:
    aggregate_payload = aggregate(canonical_results, completed)
    summary = {
        "input": str(args.input),
        "models_attempted": len(models),
        "models_succeeded": sum(1 for item in completed if item.get("ok")),
        "models_failed": sum(1 for item in completed if not item.get("ok")),
        "max_input_cost": args.max_input_cost,
        "requested_max_tokens": args.max_tokens,
        "aggregate": aggregate_payload,
        "model_runs": [
            {
                "model": item["model"],
                "ok": item["ok"],
                "elapsed_seconds": round(item["elapsed"], 3),
                "output": item["output"],
                "parsed_count": item.get("parsed_count"),
            }
            for item in completed
        ],
    }
    output_json = args.output_dir / f"{args.output_prefix}-aggregate.json"
    output_md = args.output_dir / f"{args.output_prefix}-aggregate.md"
    output_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    output_md.write_text(report_markdown(summary, output_json), encoding="utf-8")
    return output_json, output_md


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--output-prefix", default="camino-real-cheap-models")
    parser.add_argument("--flat-output", action="store_true", help="Write files directly to --output-dir instead of a run subdirectory.")
    parser.add_argument("--env", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--max-input-cost", type=float, default=1.0)
    parser.add_argument("--max-tokens", type=int, default=20000)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--concurrency", type=int, default=0, help="0 means all selected models in parallel.")
    parser.add_argument("--aggregate-only", action="store_true", help="Rebuild aggregate files from existing parsed/error files.")
    args = parser.parse_args()

    models = load_models(args.catalog, args.max_input_cost)
    if not models:
        raise RuntimeError("no models matched the cost filter")
    concurrency = args.concurrency or len(models)
    if concurrency < 1:
        raise ValueError("--concurrency must be >= 1")

    canonical_results = load_google_results(args.input)
    result_text = results_payload(canonical_results)
    base_output_dir = args.output_dir
    if not args.flat_output:
        args.output_dir = args.output_dir / args.output_prefix
    args.output_dir.mkdir(parents=True, exist_ok=True)
    file_prefix = args.output_prefix if args.flat_output else "run"

    if args.aggregate_only:
        aggregate_prefix = file_prefix
        if not any(args.output_dir.glob(f"{aggregate_prefix}-*.parsed.json")) and any(
            args.output_dir.glob(f"{args.output_prefix}-*.parsed.json")
        ):
            aggregate_prefix = args.output_prefix
        completed = load_completed_runs_from_files(models, args.output_dir, aggregate_prefix)
        original_prefix = args.output_prefix
        args.output_prefix = aggregate_prefix
        output_json, output_md = write_aggregate_report(args, canonical_results, models, completed)
        args.output_prefix = original_prefix
        print(f"Aggregate JSON: {output_json}", flush=True)
        print(f"Aggregate Markdown: {output_md}", flush=True)
        return

    api_key = load_env_key(args.env)

    manifest = {
        "input": str(args.input),
        "catalog": str(args.catalog),
        "base_output_dir": str(base_output_dir),
        "output_dir": str(args.output_dir),
        "max_input_cost": args.max_input_cost,
        "requested_max_tokens": args.max_tokens,
        "temperature": args.temperature,
        "models": [
            {
                "modelId": model["modelId"],
                "pricePerMillionInputTokens": model.get("pricePerMillionInputTokens"),
                "pricePerMillionOutputTokens": model.get("pricePerMillionOutputTokens"),
                "maxCompletionTokens": model.get("maxCompletionTokens"),
            }
            for model in models
        ],
        "started_at_unix": time.time(),
    }
    (args.output_dir / f"{file_prefix}-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    print(f"Evaluating {len(canonical_results)} Google results with {len(models)} model(s)", flush=True)
    completed = []
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {
            executor.submit(
                run_one,
                model,
                result_text,
                canonical_results,
                api_key,
                args.output_dir,
                file_prefix,
                args.max_tokens,
                args.temperature,
                args.timeout,
            ): model
            for model in models
        }
        for future in as_completed(futures):
            result = future.result()
            completed.append(result)
            status = "ok" if result["ok"] else "failed"
            extra = f", parsed {result.get('parsed_count', 0)}" if result["ok"] else ""
            print(f"{result['model']}: {status}{extra} after {result['elapsed']:.1f}s; {result['output']}", flush=True)

    original_prefix = args.output_prefix
    args.output_prefix = file_prefix
    output_json, output_md = write_aggregate_report(args, canonical_results, models, completed)
    args.output_prefix = original_prefix
    print(f"Aggregate JSON: {output_json}", flush=True)
    print(f"Aggregate Markdown: {output_md}", flush=True)


if __name__ == "__main__":
    main()
