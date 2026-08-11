#!/usr/bin/env python3
"""Run menu canonicalization for many input files with one shared work queue."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import time

from run_openrouter_menu_canonicalize import (
    DEFAULT_ENV,
    DEFAULT_MODELS,
    DEFAULT_MODELS_METADATA,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_TIMEOUT_SECONDS,
    PROMPT,
    PROMPT_WITH_CANONICAL_CATEGORY,
    PROMPT_WITH_SIDES,
    load_env_key,
    load_reasoning_efforts,
    model_slug,
    run_one_model,
)


def existing_result(output_dir: Path, output_prefix: str, model: str) -> Path | None:
    slug = model_slug(model)
    output = output_dir / f"{output_prefix}-{slug}.txt"
    error = output_dir / f"{output_prefix}-{slug}.error.json"
    if output.exists():
        return output
    if error.exists():
        return error
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", type=Path, default=DEFAULT_MODELS)
    parser.add_argument("--inputs", nargs="+", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--output-prefix-template", default="canonical-category-official-group-{stem}")
    parser.add_argument("--schema", choices=["basic", "sides", "canonical-category"], default="basic")
    parser.add_argument("--env", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--delay", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=6000)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--reasoning-effort", default=None)
    parser.add_argument("--models-metadata", type=Path, default=DEFAULT_MODELS_METADATA)
    parser.add_argument("--retry-errors", action="store_true")
    args = parser.parse_args()

    api_key = load_env_key(args.env)
    if args.schema == "sides":
        prompt = PROMPT_WITH_SIDES
    elif args.schema == "canonical-category":
        prompt = PROMPT_WITH_CANONICAL_CATEGORY
    else:
        prompt = PROMPT

    models = [line.strip() for line in args.models.read_text().splitlines() if line.strip() and not line.startswith("#")]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    reasoning_efforts = load_reasoning_efforts(args.models_metadata) if args.reasoning_effort == "auto-max" else {}

    jobs = []
    skipped = 0
    for source in args.inputs:
        output_prefix = args.output_prefix_template.format(stem=source.stem, name=source.name)
        menu_text = source.read_text(encoding="utf-8")
        for model in models:
            existing = existing_result(args.output_dir, output_prefix, model)
            if existing and (existing.suffix != ".json" or not args.retry_errors):
                skipped += 1
                continue
            reasoning_effort = reasoning_efforts.get(model) if args.reasoning_effort == "auto-max" else args.reasoning_effort
            jobs.append((model, menu_text, source, output_prefix, reasoning_effort))

    concurrency = max(1, args.concurrency)
    print(f"Running {len(jobs)} model calls across {len(args.inputs)} inputs with concurrency={concurrency}; skipped {skipped}", flush=True)
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {}
        for model, menu_text, source, output_prefix, reasoning_effort in jobs:
            print(f"Calling {source.name} :: {model} (timeout {args.timeout}s)", flush=True)
            future = executor.submit(
                run_one_model,
                model,
                menu_text,
                api_key,
                prompt,
                source,
                args.output_dir,
                output_prefix,
                args.timeout,
                args.max_tokens,
                args.temperature,
                reasoning_effort,
            )
            futures[future] = (source.name, model)
            if args.delay > 0:
                time.sleep(args.delay)

        for future in as_completed(futures):
            source_name, model = futures[future]
            try:
                message = future.result()
            except Exception as exc:
                message = f"  unexpected worker error: {type(exc).__name__}: {exc}"
            print(f"{source_name} :: {model}\n{message}", flush=True)


if __name__ == "__main__":
    main()
