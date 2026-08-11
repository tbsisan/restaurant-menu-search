#!/usr/bin/env python3
"""Run the full nachos image through OpenRouter Qwen Image 3 with a reframe prompt."""

from __future__ import annotations

import argparse
import base64
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ENV_FILE = Path.home() / "Projects/model-labs/.env.local"
SOURCE = Path("external-data/menu-scraping/image_gen_spike/fal-source-s01-square-1024.png")
OUT_DIR = Path("external-data/menu-scraping/image_gen_spike/reframe_full_source_qwen_image3_1k_2026-08-10")
MODEL = "qwen/qwen-image-3"
PROMPT = (
    "can you redo this image that is a tad more zoomed in and from a slightly more overhead perspective. "
    "Keep everything the same the lighting and food quality etc. It is a plate of nachos with orange "
    "and white melted cheese and shredded chicken."
)


def load_key() -> str:
    if os.environ.get("OPENROUTER_API_KEY"):
        return os.environ["OPENROUTER_API_KEY"]
    for line in ENV_FILE.read_text().splitlines():
        key, sep, value = line.partition("=")
        if sep and key.strip() == "OPENROUTER_API_KEY":
            return value.strip().strip('"').strip("'")
    raise SystemExit(f"OPENROUTER_API_KEY not found in {ENV_FILE}")


def request_json(url: str, key: str, payload: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=900) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        message = exc.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {message[:2000]}") from exc


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true", help="Send the paid request")
    args = parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "model": MODEL,
        "prompt": PROMPT,
        "resolution": "1K",
        "aspect_ratio": "1:1",
        "n": 1,
        "seed": 20260810,
        "input_references": [{
            "type": "image_url",
            "image_url": {"url": "data:image/png;base64," + base64.b64encode(SOURCE.read_bytes()).decode()},
        }],
    }
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "source": str(SOURCE),
        "prompt": PROMPT,
        "settings": {"resolution": "1K", "aspect_ratio": "1:1", "n": 1, "seed": 20260810},
        "mode": "run" if args.run else "dry-run",
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if not args.run:
        print(json.dumps({"dry_run": True, "output": str(OUT_DIR)}))
        return
    result = request_json("https://openrouter.ai/api/v1/images", load_key(), payload)
    (OUT_DIR / "response-raw.json").write_text(json.dumps(result, indent=2) + "\n")
    images = result.get("data") or []
    if not images or not images[0].get("b64_json"):
        raise SystemExit("Response contained no b64_json image")
    (OUT_DIR / "result.png").write_bytes(base64.b64decode(images[0]["b64_json"]))
    summary = {"id": result.get("id"), "usage": result.get("usage")}
    (OUT_DIR / "result.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
