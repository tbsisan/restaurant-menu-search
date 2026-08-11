#!/usr/bin/env python3
"""Run OpenRouter vision models against arbitrary image prompts."""

from __future__ import annotations

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
import json
import mimetypes
import re
import signal
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODELS = ROOT / "external-data/derived-untracked/image-models.txt"
DEFAULT_OUTPUT_DIR = ROOT / "external-data/openrouter_vision"
DEFAULT_ENV = Path.home() / "Projects/model-labs/.env.local"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_TIMEOUT_SECONDS = 90
DEFAULT_PROMPT = "Describe the image in detail. Do not invent details that are not visible."


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
    mime_type = mimetypes.guess_type(path.name)[0] or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def read_prompt(args: argparse.Namespace) -> str:
    if args.prompt_file:
        return args.prompt_file.read_text(encoding="utf-8").strip()
    return args.prompt


class ModelTimeoutError(TimeoutError):
    pass


@contextmanager
def wall_clock_timeout(seconds: int):
    if seconds <= 0 or threading.current_thread() is not threading.main_thread():
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


def build_content(prompt: str, image_paths: list[Path]) -> list[dict]:
    content = [{"type": "text", "text": prompt}]
    for path in image_paths:
        content.append({"type": "image_url", "image_url": {"url": image_data_url(path)}})
    return content


def call_model(
    model: str,
    prompt: str,
    image_paths: list[Path],
    api_key: str,
    timeout: int,
    max_tokens: int,
    temperature: float,
) -> dict:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": build_content(prompt, image_paths)}],
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
            "X-Title": "restaurant-menu-search general vision spike",
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
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("text"):
                parts.append(str(item["text"]))
        return "\n\n".join(parts).strip()
    return str(content).strip()


def response_markdown(model: str, prompt: str, image_paths: list[Path], response: dict) -> str:
    usage = response.get("usage") or {}
    image_lines = "\n".join(f"<!-- image: {path} -->" for path in image_paths)
    return (
        f"<!-- model: {model} -->\n"
        f"{image_lines}\n"
        f"<!-- usage: {json.dumps(usage, sort_keys=True)} -->\n\n"
        "## Prompt\n\n"
        f"{prompt.strip()}\n\n"
        "## Response\n\n"
        f"{response_text(response)}\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", type=Path, default=DEFAULT_MODELS)
    parser.add_argument("--image", type=Path, action="append", required=True)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--prompt-file", type=Path)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--output-prefix", default="vision")
    parser.add_argument("--env", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--max-tokens", type=int, default=4000)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument(
        "--concurrency",
        type=int,
        default=4,
        help="Maximum number of model calls to run in parallel; use 1 for sequential execution.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Hard wall-clock timeout in seconds for each model call; use 0 to disable.",
    )
    parser.add_argument("--delay", type=float, default=1.0)
    args = parser.parse_args()

    prompt = read_prompt(args)
    image_paths = [path.resolve() for path in args.image]
    missing = [str(path) for path in image_paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"image path does not exist: {', '.join(missing)}")

    api_key = load_env_key(args.env)
    models = [
        line.strip()
        for line in args.models.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.concurrency < 1:
        raise ValueError("--concurrency must be at least 1")

    def run_one_model(index: int, model: str) -> dict:
        if args.delay > 0 and index > 0:
            time.sleep(args.delay * index)

        slug = model_slug(model)
        output = args.output_dir / f"{args.output_prefix}-{slug}.md"
        error_output = args.output_dir / f"{args.output_prefix}-{slug}.error.json"
        started_at = time.monotonic()
        try:
            with wall_clock_timeout(args.timeout):
                response = call_model(
                    model=model,
                    prompt=prompt,
                    image_paths=image_paths,
                    api_key=api_key,
                    timeout=args.timeout,
                    max_tokens=args.max_tokens,
                    temperature=args.temperature,
                )
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
            return {
                "model": model,
                "ok": False,
                "elapsed": elapsed,
                "message": f"error {exc.code}; wrote {error_output.name}",
            }
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
            return {
                "model": model,
                "ok": False,
                "elapsed": elapsed,
                "message": f"error; wrote {error_output.name}",
            }

        elapsed = time.monotonic() - started_at
        output.write_text(response_markdown(model, prompt, image_paths, response), encoding="utf-8")
        return {
            "model": model,
            "ok": True,
            "elapsed": elapsed,
            "message": f"wrote {output.name}",
        }

    print(
        f"Calling {len(models)} models with concurrency {args.concurrency} "
        f"(timeout {args.timeout}s, delay {args.delay}s)",
        flush=True,
    )
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = {
            executor.submit(run_one_model, index, model): model
            for index, model in enumerate(models)
        }
        for future in as_completed(futures):
            model = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                print(f"{model}: unexpected runner error: {type(exc).__name__}: {exc}", flush=True)
                continue
            status = "ok" if result["ok"] else "failed"
            print(
                f"{model}: {status} after {result['elapsed']:.1f}s; {result['message']}",
                flush=True,
            )


if __name__ == "__main__":
    main()
