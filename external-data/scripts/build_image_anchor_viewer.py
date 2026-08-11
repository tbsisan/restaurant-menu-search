#!/usr/bin/env python3
"""Build a local HTML viewer for the anchored-inpainting sweep.

Writes viewer.html next to the images and references them by relative path, so
it opens straight off disk. Deliberately not a self-contained artifact: the
sweep is ~33MB of PNGs and base64-inlining them would produce an unusable file.

Layout is a matrix per dish - one row per anchor level, columns for the original
and each successive round - so the two things worth judging are adjacent:
whether the dish still looks real, and whether it still looks like *this*
restaurant's version of the dish.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

CSS = """
:root { color-scheme: light dark; --bg:#fff; --fg:#111; --muted:#666; --line:#e3e3e3; --card:#fafafa; --warn:#b4690e; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#14161a; --fg:#e9e9ea; --muted:#9aa0a6; --line:#2b2f36; --card:#1b1e24; --warn:#e0a458; }
}
* { box-sizing: border-box; }
body { margin:0; padding:24px; background:var(--bg); color:var(--fg);
       font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }
h1 { font-size:20px; margin:0 0 4px; }
h2 { font-size:16px; margin:32px 0 10px; padding-bottom:6px; border-bottom:1px solid var(--line); }
.sub { color:var(--muted); margin-bottom:20px; }
.controls { margin:16px 0; display:flex; gap:16px; align-items:center; flex-wrap:wrap; }
label { display:flex; gap:6px; align-items:center; cursor:pointer; user-select:none; }
.scroll { overflow-x:auto; }
table { border-collapse:collapse; width:100%; min-width:760px; }
th, td { padding:8px; text-align:left; vertical-align:top; border-bottom:1px solid var(--line); }
th { color:var(--muted); font-weight:600; font-size:12px; text-transform:uppercase; letter-spacing:.04em; }
.anchor { font-weight:700; white-space:nowrap; }
figure { margin:0; }
img { width:100%; max-width:260px; border-radius:6px; display:block; background:var(--card); }
.masked img { max-width:140px; opacity:.9; }
.m { font-size:11px; color:var(--muted); margin-top:6px; font-variant-numeric:tabular-nums; }
.m b { color:var(--fg); font-weight:600; }
.hot b { color:var(--warn); }
.hide { display:none; }
.note { background:var(--card); border-left:3px solid var(--line); padding:12px 14px; margin:18px 0; border-radius:0 6px 6px 0; }
code { background:var(--card); padding:1px 5px; border-radius:3px; font-size:12px; }
"""

JS = """
document.getElementById('toggleMasked').addEventListener('change', function(e) {
  document.querySelectorAll('.masked').forEach(function(el) { el.classList.toggle('hide', !e.target.checked); });
});
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dir", type=Path, default=Path("external-data/menu-scraping/image_gen_spike"))
    args = parser.parse_args()

    rows = json.loads((args.dir / "metrics.json").read_text())
    sources = {s["name"]: s for s in json.loads((args.dir / "sources.json").read_text())}
    by_source: dict[str, dict[float, dict[int, dict]]] = {}
    for row in rows:
        if not row.get("source"):
            continue
        by_source.setdefault(row["source"], {}).setdefault(row["anchor_percent"], {})[row["round"]] = row

    max_round = max((r.get("round") or 0) for r in rows)
    parts = [
        "<!doctype html><meta charset='utf-8'><title>Anchored inpainting sweep</title>",
        f"<style>{CSS}</style>",
        "<h1>Anchored inpainting &mdash; anchor fraction sweep</h1>",
        "<div class='sub'>Each row keeps a fixed % of the previous image as scattered patches and regenerates "
        "the rest. Round N anchors on round N&minus;1, so the original washes out progressively.</div>",
        "<div class='note'><b>Reading the numbers.</b> "
        "<code>subject</code> is literal pixel retention measured <i>excluding flat backdrop</i> &mdash; raw "
        "retention counts backdrop-matching-backdrop as copying and overstates it badly (30.4% raw vs 2.6% real "
        "on one cell). <code>phash</code> is perceptual distance from the original (higher = more different, 63 max). "
        "<code>colour</code> is coarse palette drift (lower = closer to the real dish).</div>",
        "<div class='controls'><label><input type='checkbox' id='toggleMasked'> show masked inputs actually sent</label></div>",
    ]

    for name, anchors in by_source.items():
        source = sources.get(name, {})
        parts.append(f"<h2>{name}</h2>")
        parts.append(f"<div class='sub'>{source.get('description','')}</div>")
        parts.append("<div class='scroll'><table><tr><th>Anchor</th><th>Original</th>")
        parts.extend(f"<th>Round {i}</th>" for i in range(1, max_round + 1))
        parts.append("</tr>")
        for percent in sorted(anchors):
            parts.append(f"<tr><td class='anchor'>{percent:g}%</td>")
            src_rel = Path(source.get("path", "")).name
            parts.append(f"<td><figure><a href='{src_rel}' target='_blank'><img src='{src_rel}' alt='original'></a>"
                         "<div class='m'>source photo</div></figure></td>")
            for round_index in range(1, max_round + 1):
                row = anchors[percent].get(round_index)
                if not row:
                    parts.append("<td>&mdash;</td>")
                    continue
                stem = f"s{source.get('index', 1):02d}-a{percent:g}-r{round_index}"
                hot = " hot" if row.get("subject_retention", 0) >= 0.02 else ""
                parts.append(
                    f"<td><figure>"
                    f"<a href='{stem}-out.png' target='_blank'><img src='{stem}-out.png' alt='round {round_index}'></a>"
                    f"<div class='m{hot}'>subject <b>{row.get('subject_retention', 0):.4f}</b> &middot; "
                    f"phash <b>{row.get('phash_hamming','?')}</b> &middot; "
                    f"colour <b>{row.get('coarse_colour_delta','?')}</b></div>"
                    f"<div class='masked hide'><img src='{stem}-input.png' alt='masked input'></div>"
                    f"</figure></td>"
                )
            parts.append("</tr>")
        parts.append("</table></div>")

    parts.append(f"<script>{JS}</script>")
    out = args.dir / "viewer.html"
    out.write_text("\n".join(parts), encoding="utf-8")
    print(f"Wrote {out}\nOpen with:  xdg-open {out}")


if __name__ == "__main__":
    main()
