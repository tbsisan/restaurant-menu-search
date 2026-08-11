#!/usr/bin/env python3
"""Run the five anchor crops through OpenRouter Qwen Image 3."""

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
CROP_DIR = Path("external-data/menu-scraping/image_gen_spike/outpaint_anchor_crops_1024")
OUT_DIR = Path("external-data/menu-scraping/image_gen_spike/outpaint_openrouter_qwen_image3_anchor_shapes_1k_2026-08-10")
MODEL = "qwen/qwen-image-3"
PROMPT = (
    "Outpaint this image crop into a complete square image, regenerating the missing surrounding parts "
    "while continuing naturally from the provided pixels. It is a plate of nachos with just chips, "
    "orange and white cheese, and shredded chicken."
)
CASES = ["center-square-320", "center-square-512", "left-half-512", "center-strip-128", "center-strip-256"]


def load_key() -> str:
    if os.environ.get("OPENROUTER_API_KEY"):
        return os.environ["OPENROUTER_API_KEY"]
    for line in ENV_FILE.read_text().splitlines():
        key, sep, value = line.partition("=")
        if sep and key.strip() == "OPENROUTER_API_KEY":
            return value.strip().strip('"').strip("'")
    raise SystemExit(f"OPENROUTER_API_KEY not found in {ENV_FILE}")


def request_json(url: str, key: str, payload: dict | None = None) -> dict:
    body = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="GET" if payload is None else "POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=900) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        message = exc.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {message[:2000]}") from exc


def payload_for(name: str) -> dict:
    image = (CROP_DIR / f"{name}.png").read_bytes()
    data_url = "data:image/png;base64," + base64.b64encode(image).decode()
    return {
        "model": MODEL,
        "prompt": PROMPT,
        "resolution": "1K",
        "aspect_ratio": "1:1",
        "n": 1,
        "seed": 20260810,
        "input_references": [{"type": "image_url", "image_url": {"url": data_url}}],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true", help="Send paid network requests")
    args = parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "model": MODEL,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "prompt": PROMPT,
        "settings": {"resolution": "1K", "aspect_ratio": "1:1", "n": 1, "seed": 20260810},
        "cases": CASES,
        "mode": "run" if args.run else "dry-run",
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if not args.run:
        print(json.dumps({"dry_run": True, "cases": len(CASES), "output": str(OUT_DIR)}))
        return

    key = load_key()
    endpoints = request_json(f"https://openrouter.ai/api/v1/images/models/{MODEL}/endpoints", key)
    (OUT_DIR / "model-endpoints.json").write_text(json.dumps(endpoints, indent=2) + "\n")
    completed = 0
    total_cost = 0.0
    for name in CASES:
        record: dict
        try:
            result = request_json("https://openrouter.ai/api/v1/images", key, payload_for(name))
            (OUT_DIR / f"{name}-raw.json").write_text(json.dumps(result, indent=2) + "\n")
            images = result.get("data") or []
            if not images or not images[0].get("b64_json"):
                raise RuntimeError("Response contained no b64_json image")
            (OUT_DIR / f"{name}.png").write_bytes(base64.b64decode(images[0]["b64_json"]))
            usage = result.get("usage") or {}
            total_cost += float(usage.get("cost") or 0)
            record = {"name": name, "usage": usage, "id": result.get("id")}
            completed += 1
        except Exception as exc:
            record = {"name": name, "error": repr(exc)}
        (OUT_DIR / f"{name}.json").write_text(json.dumps(record, indent=2) + "\n")
    summary = {"completed": completed, "failed": len(CASES) - completed, "reported_cost_usd": total_cost}
    (OUT_DIR / "results.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
