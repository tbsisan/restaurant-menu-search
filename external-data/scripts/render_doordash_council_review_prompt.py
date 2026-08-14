#!/usr/bin/env python3
"""Render a self-contained AI Council code-review prompt for the DoorDash spike.

Usage:
  python external-data/scripts/render_doordash_council_review_prompt.py > /tmp/doordash-council-review.md

The generated prompt embeds the current capture script verbatim so code review
always follows the working copy, rather than a pasted snapshot that can drift.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "external-data/scripts/spike_doordash_network_capture.py"


INTRODUCTION = r"""# DoorDash menu-capture code review

You are reviewing one component of an early-stage restaurant-menu scraping system. Be a practical, skeptical senior Python and browser-automation engineer. This is a design/code review, not a request to rewrite the program wholesale.

## Product task and operating constraints

The product needs structured restaurant menus from DoorDash: category membership, every item, price information, item-level popularity where visible, and full configuration data (required/optional modifier groups, selection limits, size-dependent choices, nested options, and option prices). The target is eventually a reliable multi-restaurant scraper, but the supplied program remains an exploratory/spike capture tool.

It communicates with a running `camofox-browser` REST server. The browser itself navigates DoorDash and is configured with a restaurant-local geolocation, locale, timezone, and humanized browser behavior. The Python client uses Camofox's browser APIs; it does not directly fetch DoorDash pages.

The key discovery behind this design is that DoorDash's page JSON-LD is incomplete and has no modifier tree. The rendered store page lazily/virtually renders menu cards as scrolling occurs, while opening an item causes a GraphQL `itemPage` payload to become available. The script collects virtualized item cards across controlled scrolling, then requests/captures each item's `itemPage` data in the live browser context.

## Known gotchas that deserve explicit scrutiny

- The menu is virtualized: one DOM query only sees roughly the current viewport. A small menu can entirely fit on initial render, while a large one requires scrolling. The review should examine collection completion, duplicate handling, scroll-stall behavior, category attribution, and what happens when a lazy batch never arrives.
- DoorDash's embedded JSON-LD is a partial lower bound, not a complete menu truth. In samples it omits whole categories and duplicates items in a "Most Ordered" category.
- Item configuration is a nested tree. A size/style choice may expose its own modifier groups, so a flat option representation is deliberately avoided downstream.
- Browser tabs/sessions can disappear mid-run. The script attempts recovery and checkpoints each fetched item to allow resume.
- The browser/server can return changed shapes, null fields, modal/interstitial states, 4xx/5xx responses, incomplete network bodies, or a page that superficially renders but is not usable.
- Scraping must not convert an incomplete capture into a deceptively successful final artifact. It should make incomplete/failure states diagnosable.
- The current pacing aims to avoid an identical top-to-bottom request sequence. Evaluate it for correctness and maintainability, but do not recommend evading access controls, CAPTCHAs, or site protections.
- The code may be run manually via subcommands (`open`, `record`, `probe`, `click`, `dump`, `items`, `harvest`, `close`) and later invoked by higher-level automation. Assume no external orchestrator guarantees perfect state.

## Neighboring offline parsers (context only; not included)

`parse_doordash_itempage.py` consumes the harvest JSON and preserves the `optionLists` modifier tree, separates cross-sell "item" groups from modifiers, produces a flattened search index, derives cautious dietary badges, computes required-configuration price ranges, and can attach card and restaurant ratings.

`parse_doordash_jsonld.py` is an older/fallback parser for embedded JSON-LD. It extracts basic restaurant/menu data and reconciles it with card data, but it is knowingly incomplete and cannot recover modifiers. Do not spend review space proposing that JSON-LD replace the `itemPage` capture route.

## Review target: `spike_doordash_network_capture.py`

```python
"""

TASK = r"""
```

## Your assigned review task

Review the code above in depth. Reason from the exact implementation, not only from the task description. Do not assume an endpoint works merely because its name sounds right.

Return the review in this format:

1. **Executive assessment** — whether this is a sound spike foundation, in 3–6 sentences.
2. **Findings, ordered by severity** — each finding must include:
   - severity: `critical`, `high`, `medium`, or `low`;
   - exact function/line-region or a distinctive code quote;
   - failure scenario;
   - impact on menu completeness, correctness, resumability, cost, or operability;
   - a proportionate concrete fix.
   Do not invent findings: if something is speculative, label it as such and say what observation/test would validate it.
3. **Completeness and correctness checks** — identify the smallest set of evidence and invariants this script should persist or assert to distinguish a full menu capture from a partial/quietly broken run. Address small menus that require no scrolling.
4. **Architecture recommendation** — distinguish changes worth making now in this spike from abstractions that should wait until multiple provider scrapers actually need them. In particular, assess boundaries among browser control, menu discovery/collection, GraphQL capture, checkpointing, pacing, and later offline parsing.
5. **Prioritized next actions** — no more than eight items, ordered, each marked either `code change`, `test`, or `operational check`.

Stay grounded in this program's stated constraints. Favor durable, observable behavior over cleverness. Do not give generic scraping advice, do not propose bypassing bot checks or access controls, and do not recommend changing unrelated parser scripts unless an interface contract makes it necessary.
```
"""


def main() -> None:
    source = TARGET.read_text(encoding="utf-8").rstrip()
    print(INTRODUCTION + source + TASK)


if __name__ == "__main__":
    main()
