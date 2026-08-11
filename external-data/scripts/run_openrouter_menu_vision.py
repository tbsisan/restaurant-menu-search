#!/usr/bin/env python3
"""Run OpenRouter vision models against a menu image and save markdown outputs."""

from __future__ import annotations

import argparse
import base64
from contextlib import contextmanager
import json
import os
import re
import signal
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODELS = ROOT / "external-data/derived-untracked/image-models.txt"
DEFAULT_IMAGE = ROOT / "external-data/menu-scraping/official_site/images-quarter/marias-flyer-menu-page-01.png"
DEFAULT_OUTPUT_DIR = ROOT / "external-data/menu-scraping/openrouter_vision"
DEFAULT_ENV = Path.home() / "Projects/model-labs/.env.local"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_TIMEOUT_SECONDS = 90


PROMPT = """This is a menu image from a Mexican restaurant.

Please extract all visible text from the menu image in a reasonable Markdown format.
The text may include dish names, descriptions, prices, hours, address, phone number, sections, footnotes, and ordering notes.

Preserve the menu structure as best you can:
- Use headings for sections.
- Use bullet lists or tables for dishes.
- Include descriptions and prices when visible.
- Do not invent missing text.
- If text is unclear, mark it as [unclear].
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


def image_data_url(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


class ModelTimeoutError(TimeoutError):
    pass


@contextmanager
def wall_clock_timeout(seconds: int):
    if seconds <= 0:
        yield
        return

    def raise_timeout(_signum, _frame) -> None:
        raise ModelTimeoutError(f"exceeded {seconds}s wall-clock timeout")

    previous_handler = signal.signal(signal.SIGALRM, raise_timeout)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)


def call_model(model: str, data_url: str, api_key: str, timeout: int) -> dict:
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        "temperature": 0,
        "max_tokens": 4000,
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OPENROUTER_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/tbsisan/restaurant-menu-search",
            "X-Title": "restaurant-menu-search menu OCR spike",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def response_markdown(model: str, image: Path, response: dict) -> str:
    choice = (response.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    content = message.get("content") or ""
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("text"):
                parts.append(str(item["text"]))
        content = "\n\n".join(parts)

    usage = response.get("usage") or {}
    return (
        f"<!-- model: {model} -->\n"
        f"<!-- image: {image} -->\n"
        f"<!-- usage: {json.dumps(usage, sort_keys=True)} -->\n\n"
        f"{str(content).strip()}\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", type=Path, default=DEFAULT_MODELS)
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--output-prefix", default="menu-flyer-1")
    parser.add_argument("--env", type=Path, default=DEFAULT_ENV)
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Hard wall-clock timeout in seconds for each model call; use 0 to disable.",
    )
    parser.add_argument("--delay", type=float, default=1.0)
    args = parser.parse_args()

    api_key = load_env_key(args.env)
    models = [line.strip() for line in args.models.read_text().splitlines() if line.strip() and not line.startswith("#")]
    data_url = image_data_url(args.image)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for model in models:
        slug = model_slug(model)
        output = args.output_dir / f"{args.output_prefix}-{slug}.md"
        error_output = args.output_dir / f"{args.output_prefix}-{slug}.error.json"
        print(f"Calling {model} (timeout {args.timeout}s)", flush=True)
        started_at = time.monotonic()
        try:
            with wall_clock_timeout(args.timeout):
                response = call_model(model, data_url, api_key, args.timeout)
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
            print(f"  error {exc.code} after {elapsed:.1f}s; wrote {error_output.name}", flush=True)
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
            print(f"  error after {elapsed:.1f}s; wrote {error_output.name}", flush=True)
        else:
            elapsed = time.monotonic() - started_at
            output.write_text(response_markdown(model, args.image, response), encoding="utf-8")
            print(f"  wrote {output.name} after {elapsed:.1f}s", flush=True)
        time.sleep(args.delay)


if __name__ == "__main__":
    main()
