#!/usr/bin/env python3
"""Anchored-inpainting spike: how little of a real dish photo do you need?

Premise under test: keep a small fraction of a real photo (scattered patches),
have an image model generate everything else, then repeat - each round anchoring
on the *previous generation* rather than the original. The hope is that a few
percent of anchor is enough to keep the result faithful to the actual dish
(portion, sauce colour, plating, lighting) while the original's pixels wash out
over successive rounds.

Two questions, and the script measures both rather than eyeballing them:

  1. Quality/faithfulness - does 1% anchor produce something that still looks
     like the real dish, or does it drift into generic stock food?
  2. Remnant retention - how much of the original literally survives? This is
     the question that decides whether the output is a derivative work. Reported
     as `literal_retention` (fraction of pixels still within tolerance of the
     original) plus perceptual distance (pHash Hamming, coarse colour delta).

Retention is measured against the ORIGINAL at every round, never against the
previous round, so round-N numbers answer "what is left of the source photo".

Outputs per (source, anchor%, round): the masked input actually sent, the
generated image, and a metrics row. Everything lands in --out-dir with a
metrics.json summarising the sweep.

Note the sweep costs real money - roughly $0.04 per generated image on
gemini-2.5-flash-image at the time of writing, so a 4-anchor x 3-round x
2-source run is ~$1. --dry-run prints the plan and cost estimate without
calling the API.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import random
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from scipy.fft import dct

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_ENV = Path.home() / "Projects/model-labs/.env.local"
COMPARE_SIZE = (512, 512)

PROMPT = (
    "This is a photograph of a dish with most of the image missing (shown as "
    "transparent/blank). Reconstruct the complete photograph. The visible "
    "fragments are ground truth: match their lighting, colour, sauce tones, "
    "portion size and plating style exactly, and extend them into a coherent, "
    "photorealistic image of the same dish on the same plate. Do not stylise. "
    "Output a single realistic food photograph.\n\nDish: {name}\n{description}"
)


def load_api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key
    for path in (DEFAULT_ENV, Path(".env.local"), Path(".env")):
        if path.exists():
            for line in path.read_text().splitlines():
                if line.startswith("OPENROUTER_API_KEY"):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("OPENROUTER_API_KEY not found")


def make_anchor_mask(size: tuple[int, int], fraction: float, patches: int, rng: random.Random) -> Image.Image:
    """Boolean mask (white = keep) of `patches` square blocks covering roughly
    `fraction` of the image. Squares scattered uniformly - a single contiguous
    blob would hand the model a much easier problem than real usage."""
    width, height = size
    total = width * height
    per_patch = (total * fraction) / max(patches, 1)
    side = max(4, int(round(per_patch ** 0.5)))
    mask = Image.new("L", size, 0)
    pixels = mask.load()
    for _ in range(patches):
        x0 = rng.randint(0, max(0, width - side))
        y0 = rng.randint(0, max(0, height - side))
        for y in range(y0, min(y0 + side, height)):
            for x in range(x0, min(x0 + side, width)):
                pixels[x, y] = 255
    return mask


def apply_mask(image: Image.Image, mask: Image.Image, fill: tuple[int, int, int] = (128, 128, 128)) -> Image.Image:
    """Blank the masked region in BOTH colour and alpha.

    Setting alpha alone is not enough and is actively misleading: PNG stores RGB
    independently of the alpha channel, so a merely-transparent region still
    carries every original pixel. A model that flattens or ignores alpha - which
    many pipelines do - would then receive the complete source photo while the
    file *looked* 95% blank. That would silently turn a "1% anchor" run into a
    100% anchor run and invalidate the whole sweep.

    So the masked area is composited onto neutral grey first, and alpha is set
    afterwards. Models honouring alpha see transparency; models flattening it
    see grey. Neither sees the original.
    """
    base = Image.new("RGB", image.size, fill)
    composited = Image.composite(image.convert("RGB"), base, mask)
    out = composited.convert("RGBA")
    out.putalpha(mask)
    return out


def phash(image: Image.Image) -> np.ndarray:
    grey = np.asarray(image.convert("L").resize((32, 32), Image.LANCZOS), dtype=float)
    coeffs = dct(dct(grey, axis=0, norm="ortho"), axis=1, norm="ortho")[:8, :8]
    flat = coeffs.flatten()[1:]  # drop DC
    return flat > np.median(flat)


def subject_mask(pixels: np.ndarray, tolerance: int = 18) -> np.ndarray:
    """True where the image is *not* flat studio background.

    Estimated from the median colour of three corners. Food photos are often
    ~40% seamless backdrop, and two independently-generated flat backdrops of
    the same colour match pixel-for-pixel without anything having been copied.
    """
    corners = np.concatenate([
        pixels[:20, :20].reshape(-1, 3),
        pixels[:20, -20:].reshape(-1, 3),
        pixels[-20:, :20].reshape(-1, 3),
    ])
    background_colour = np.median(corners, axis=0)
    return np.abs(pixels - background_colour).max(axis=2) > tolerance


def metrics_against_original(original: Image.Image, candidate: Image.Image, tolerance: int = 10) -> dict[str, float]:
    a = np.asarray(original.convert("RGB").resize(COMPARE_SIZE, Image.LANCZOS), dtype=np.int16)
    b = np.asarray(candidate.convert("RGB").resize(COMPARE_SIZE, Image.LANCZOS), dtype=np.int16)
    matches = np.abs(a - b).max(axis=2) <= tolerance
    literal = float(matches.mean())

    # Raw retention is badly inflated by backdrop: measured on one sample,
    # 94.7% of "retained" pixels were background-matching-background, turning a
    # true 2.6% into a headline 30.4%. Subject-only retention is the number that
    # actually speaks to whether protected expression survived.
    subject = subject_mask(a)
    subject_retention = float(matches[subject].mean()) if subject.any() else 0.0

    hamming = int(np.count_nonzero(phash(original) != phash(candidate)))
    coarse_a = np.asarray(original.convert("RGB").resize((16, 16), Image.LANCZOS), dtype=float)
    coarse_b = np.asarray(candidate.convert("RGB").resize((16, 16), Image.LANCZOS), dtype=float)
    return {
        "subject_retention": round(subject_retention, 4),
        "literal_retention": round(literal, 4),
        "background_share": round(float(1.0 - subject.mean()), 3),
        "phash_hamming": hamming,
        "mean_abs_delta": round(float(np.abs(a - b).mean()), 2),
        "coarse_colour_delta": round(float(np.abs(coarse_a - coarse_b).mean()), 2),
    }


def generate(key: str, model: str, image: Image.Image, name: str, description: str, timeout: int) -> Image.Image | None:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode()
    body = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT.format(name=name, description=description or "")},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}"}},
                ],
            }
        ],
        "modalities": ["image", "text"],
    }
    request = urllib.request.Request(
        OPENROUTER_URL,
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        response = json.load(urllib.request.urlopen(request, timeout=timeout))
    except urllib.error.HTTPError as exc:
        print(f"      HTTP {exc.code}: {exc.read()[:200].decode(errors='replace')}")
        return None
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"      request failed: {exc}")
        return None
    images = (response.get("choices") or [{}])[0].get("message", {}).get("images") or []
    if not images:
        return None
    payload = images[0]["image_url"]["url"].split(",", 1)[1]
    return Image.open(io.BytesIO(base64.b64decode(payload)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sources", type=Path, default=Path("external-data/menu-scraping/image_gen_spike/sources.json"))
    parser.add_argument("--out-dir", type=Path, default=Path("external-data/menu-scraping/image_gen_spike"))
    parser.add_argument("--anchor-percents", type=float, nargs="+", default=[1, 2, 5, 10])
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--patches", type=int, default=14)
    parser.add_argument("--limit-sources", type=int, default=2)
    parser.add_argument("--model", default="google/gemini-2.5-flash-image")
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--concurrency", type=int, default=8,
                        help="chains in flight; rounds within a chain stay sequential")
    parser.add_argument("--reuse", action="store_true", default=True,
                        help="score existing -out.png instead of regenerating (default on)")
    parser.add_argument("--no-reuse", dest="reuse", action="store_false")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    sources = json.loads(args.sources.read_text())[: args.limit_sources]
    calls = len(sources) * len(args.anchor_percents) * args.rounds
    print(f"{len(sources)} sources x {len(args.anchor_percents)} anchor levels x {args.rounds} rounds "
          f"= {calls} generations (~${calls * 0.04:.2f})")
    if args.dry_run:
        return

    key = load_api_key()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    def run_chain(source: dict[str, Any], percent: float) -> list[dict[str, Any]]:
        """One (dish, anchor%) chain. Rounds are inherently sequential - round
        N+1 anchors on round N's output - but chains are independent, which is
        where the parallelism comes from."""
        original = Image.open(source["path"]).convert("RGB")
        name = source["name"]
        # Per-chain seed keeps patch layouts reproducible regardless of the
        # order threads happen to finish in.
        rng = random.Random(f"{args.seed}-{source['index']}-{percent}")
        fraction = percent / 100.0
        current = original
        out: list[dict[str, Any]] = []
        for round_index in range(1, args.rounds + 1):
            stem = f"s{source['index']:02d}-a{percent:g}-r{round_index}"
            out_path = args.out_dir / f"{stem}-out.png"
            if args.reuse and out_path.exists():
                # Already generated by an earlier run - score it, don't re-buy it.
                generated = Image.open(out_path).convert("RGB")
                reused = True
            else:
                mask = make_anchor_mask(current.size, fraction, args.patches, rng)
                masked = apply_mask(current, mask)
                masked.save(args.out_dir / f"{stem}-input.png")
                generated = generate(key, args.model, masked, name, source.get("description", ""), args.timeout)
                reused = False
                if generated is None:
                    print(f"  [{name[:18]:<18} a{percent:g}% r{round_index}] FAILED")
                    out.append({"source": name, "anchor_percent": percent, "round": round_index, "error": "no image"})
                    break
                generated.save(out_path)
            stats = metrics_against_original(original, generated)
            stats.update({"source": name, "anchor_percent": percent, "round": round_index,
                          "output": f"{stem}-out.png", "reused": reused})
            out.append(stats)
            print(f"  [{name[:18]:<18} a{percent:g}% r{round_index}]{' (reused)' if reused else ''} "
                  f"retention={stats['literal_retention']:.4f} "
                  f"phash={stats['phash_hamming']}/63 colour_delta={stats['coarse_colour_delta']}")
            current = generated
        return out

    chains = [(s, p) for s in sources for p in args.anchor_percents]
    rows: list[dict[str, Any]] = []
    started = time.time()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = {pool.submit(run_chain, s, p): (s["index"], p) for s, p in chains}
        for future in as_completed(futures):
            try:
                rows.extend(future.result())
            except Exception as exc:  # one bad chain shouldn't lose the sweep
                index, percent = futures[future]
                print(f"  chain s{index} a{percent}% raised: {exc}")
                rows.append({"source_index": index, "anchor_percent": percent, "error": str(exc)})

    rows.sort(key=lambda r: (str(r.get("source")), r.get("anchor_percent") or 0, r.get("round") or 0))
    (args.out_dir / "metrics.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"\nWrote {args.out_dir / 'metrics.json'} ({len(rows)} rows) in {time.time()-started:.0f}s "
          f"across {len(chains)} chains at concurrency {args.concurrency}")


if __name__ == "__main__":
    main()
