# DoorDash harvest implementation: code review

**Date:** 2026-08-14
**Reviewing:** the uncommitted changes made against
`DOORDASH_HARVEST_IMPLEMENTATION_PLAN.md`, and the fix claims recorded in
`doordash-harvest-validation-checklist.md`.

**Files reviewed:**

- `external-data/scripts/spike_doordash_network_capture.py` (+1131 / -128)
- `external-data/scripts/parse_doordash_itempage.py` (+75)
- `external-data/scripts/normalize_menu_sizes.py` (+49) — *added 2026-08-14 after
  the rebuttal correctly noted it was missing from the original scope*
- `external-data/menu-scraping/doordash-menu-scraping-notes.md` (+47)

> **Revision note (2026-08-14).** This document was amended after
> `doordash-harvest-code-review-rebuttal-2026-08-14.md`. Two corrections and one
> added finding are marked inline. The rebuttal accepts every substantive
> finding below; where it qualifies one, the qualification is recorded at that
> finding.

## Method

The diff was read in full, then the claimed safeguards were **executed** rather
than only inspected: a throwaway harness drove the real functions with a fake
Camofox client and scripted page states, covering every `fetch_item_page`
branch, the discovery outcomes, and the resume/checkpoint paths. A synthetic
duplicate-category harvest was run through the real parser CLI.

**28 of 30 behavioural checks passed.**

Searches for supporting evidence were done against the filesystem, not git, so
uncommitted work was still in scope:

- `find` for `test_*.py` / `*_test.py` / `conftest.py` — **correction:** the
  original wording of this review said no such file exists anywhere in the
  project. That is literally false, as the rebuttal notes:
  `run_openrouter_qwen_image3_reframe_test.py` matches. The accurate statement
  is that **no test file covering the DoorDash harvest exists**, and no
  `conftest.py` or test runner configuration exists anywhere. The substantive
  finding is unchanged.
- `grep -rl '"schema_version": 2'` across `external-data/**.json` — no matches.
- `find external-data -name '*.discovery.json'` — no matches.
- `ls DOORDASH_HARVEST_COUNCIL_HANDOFF.md` — not present.

## Verdict

The engineering is substantially real and mostly correct. The artifact-honesty
machinery that was the point of the plan genuinely works. What is overstated is
the *evidence*: one checklist claim is false, and the discovery rewrite has
never been executed even once.

## Confirmed working (verified by execution, not reading)

| Area | Result |
| --- | --- |
| `fetch_item_page` diagnostics | All 11 branches return the correct specific `kind`: `http_error`, `graphql_errors`, `response_not_json`, `missing_item_page`, `malformed_item_page`, `malformed_response_wrapper`, `item_identity_mismatch`, `network_fetch_error`, `camofox_evaluate_error`, `camofox_evaluate_invalid_result`, plus `success`. |
| Completeness gating | `build_harvest_status` refuses `complete` for capped discovery, `--limit`, `--items-file`, empty selection, failures, and pending captures. Top-level `complete` is derived from `harvest.state`, never asserted by a caller. |
| Discovery outcomes | No-scroll menu → `bottom_stable` / `complete`. Bot-check page → `page_problem_signaled`, `page_usable: "no"`. Still-growing menu at cap → `scroll_limit_reached` / `incomplete`. Zero items is never promoted to success. |
| Resume safety | Refuses store-id mismatch, store-url mismatch, selection mismatch, non-JSON, and pre-contract artifacts. `in_progress` discovery sidecars are never reused as complete. |
| Retry/duplicate hygiene | `upsert_capture_result` keeps one record per item id, and a later transient failure cannot overwrite an already-validated payload. |
| Duplicate categories | Checklist row 3 holds. A synthetic item in `Tacos` + `Most Ordered` parsed to one `source_item_id` with both `section_memberships`, emitted under both categories: 2 unique items → 3 category placements. |

## Findings

### 1. The fixture-test claim is false — HIGH

`doordash-harvest-validation-checklist.md:17` states: *"Fixture tests already
cover these branches."*

There is no test file anywhere in the project — no `test_*.py`, no `conftest.py`,
no self-test subcommand. The branches do behave correctly, but nothing in the
repo demonstrates that or would catch a regression. This is the one claim in the
checklist that asserts work already done rather than work outstanding, and it is
the one that is not true.

### 2. Browser loss during discovery is unhandled — HIGH

`spike_doordash_network_capture.py:698-811` (`collect_items`)

Checklist row 5 claims: *"The discovery sidecar is saved as `in_progress`, is
never reused as complete, and a subsequent run starts safely."*

The second and third clauses hold. The first does not, in the way it implies.
`collect_items` has **no exception handling around any `client.evaluate` call**.
When the tab or browser dies, `CamofoxClient._post` raises `requests.HTTPError`
via `raise_for_status()`, and that propagates straight out of `collect_items`
through `cmd_harvest` as an uncaught traceback. The run produces:

- no `discovery` record,
- no harvest file at all,
- an `in_progress` sidecar **only if** at least one batch had already been
  checkpointed by `checkpoint_callback`.

The item-capture path handles exactly this failure correctly (returns
`camofox_evaluate_error`, checkpoints, attempts recovery). Discovery was not
given the same treatment. Reproduced in the harness: `uncaught HTTPError escapes
collect_items`.

### 3. `retryable: true` is recorded but never acted on — MEDIUM

`spike_doordash_network_capture.py:1214-1220`, `:1244-1250`, `:1464`

`fetch_item_page` marks `network_fetch_error` and `http_error` on 408 / 429 /
5xx as `retryable: true`. The harvest loop retries only:

```python
if diagnostic["kind"] in {"camofox_evaluate_error", "camofox_evaluate_invalid_result"} and attempt < 2:
```

So a 503 or a network fetch error gets exactly one attempt and is then persisted
into the artifact carrying `retryable: true`. A reviewer reading that artifact —
which is precisely the audience the plan's "Done when" section names — would
reasonably conclude a retry was attempted. It was not.

### 4. `--ratings` silently destroys ratings already in the harvest — MEDIUM

`parse_doordash_itempage.py:313-316`

```python
entries = [{**entry, **{
    "like_percent": ratings_by_id.get(entry.get("item_id"), {}).get("like_percent"),
    "like_review_count": ratings_by_id.get(entry.get("item_id"), {}).get("like_review_count"),
}} for entry in entries]
```

The dict merge is unconditional, so every entry gets both keys overwritten —
with `None` when the ratings file does not list that item. Demonstrated: an item
carrying `like_percent: 92, like_review_count: 48` in the harvest came out
`null` / `null` because the supplied ratings file only covered a different item.

This is newly dangerous because the scraper now collects card ratings inline
(`COLLECT_STEP_JS`, the `ratingMatch` block), so the harvest is often the better
source. Note also that `parse_item:277` uses `if "like_percent" in entry`, which
correctly distinguishes absent from null — that care is undone by this merge
always inserting the key.

### 5. `--sample-per-section` still uses collection order — MEDIUM

`spike_doordash_network_capture.py:1401`

```python
by_section.setdefault(str(item.get("section") or "?"), []).append(item)
```

Plan priority 3 says *"Collection order must not silently decide the menu
structure."* The `sections` list was added for exactly that reason, and
`summarize_discovery` and the parser both honour it — but sampling still buckets
by `section`, the backward-compatible first-observed value. A stratified sample
therefore cannot sample a recommendation shelf, and which bucket an item lands
in depends on which card mounted first.

### 6. Normalizer summary statistics double-count cross-listed items — MEDIUM

*Added 2026-08-14, after the rebuttal correctly flagged that
`normalize_menu_sizes.py` was outside the original review scope.*

`normalize_menu_sizes.py:331-356`

The rebuttal's description of this file is accurate and I verified it: on merge,
`merge_group` does preserve `source_item_ids` (the union of the merged variants'
IDs) and the union of `section_memberships`. That part is correct and works.

What neither document caught is an interaction defect. The parser now emits one
item into **every** category it appeared in, so a cross-listed dish is present
as two placements. The normalizer iterates
`for section in menu_sections: for item in section["items"]` and processes each
placement independently, so every counter it reports counts *placements, not
items*. Verified end to end on a synthetic two-variant, cross-listed family:

```
parse:     2 sections, 2 unique items, 4 category placements
normalize: 2 items after merging 2 size duplicates
           {"size_items_merged": 2, ...}
```

One two-variant family merged once per section and was reported as
`size_items_merged: 2`. A separate run with menu codes reported
`menu_codes_extracted: 4` for two source items. The headline
`N items after merging` is likewise a placement count.

This matters beyond cosmetics, for two reasons:

- The parser was deliberately taught to distinguish "unique items" from
  "category placements" in its own summary line. The normalizer, changed in the
  same batch, was not — so the two stages now report incompatible units.
- `doordash-menu-scraping-notes.md` records figures computed *before* duplicate
  emission existed ("113 of the 143 titles had a leading code", "The run
  normalized 17 display titles in all"). Re-running those stores will now
  produce larger numbers. That is expected, not a regression, but nothing
  currently says so and it will read as one.

The merged output itself is correct — the same merged dish under two sections
with identical `source_item_ids` is the intended shape. Only the counting is
wrong.

### 7. Minor issues — LOW

- **Progress counter mismatch.** Success lines print `[{i}/{len(items)}]`
  (`:1521`); failure and recovery lines print `[{i}/{len(fetch_order)}]`
  (`:1502`, `:1466`). On a resumed run these denominators differ, so the console
  log contradicts itself.
- **`cmd_items` section tally.** `:1313` uses `it["section"]` directly
  (KeyError-prone) after `:1312` used the safe `it.get("section")`. It also
  counts by `section` only, so the printed tally disagrees with the `sections`
  data it just wrote.
- **Two-phase workflow can never pass.** `--items-file` forces
  `selection.source: "items_file"` → reason `item_selection_not_live_verified` →
  `state: "incomplete"`, permanently. The `items` → `harvest --items-file`
  workflow therefore cannot satisfy the checklist's own "Normal full-scrape
  success criterion". That may be the intended strictness, but it should be a
  recorded decision rather than an accident.

## Unvalidated behaviour change (not a defect, but untested)

Collection previously used a single selector, `[data-testid="MenuItem"]`. It now
uses all six of `MENU_CARD_SELECTORS` (`:42-49`), including
`a[href*="?itemId="]` and `a[href*="/item/"]`. Any card is still gated on
yielding an item id, so stray links are excluded — but this genuinely changes
what a "complete" menu contains relative to every previously validated harvest
(jets-pizza, china-house, china-1, tru-pizza, habibs, hungry-howies,
marias). It has not been run once against a live page.

## Validation status

No artifact anywhere in the project carries `schema_version: 2`, and no
`.discovery.json` sidecar exists. All eight existing harvests are pre-contract:

| Harvest | items | `harvest` block |
| --- | --- | --- |
| china-1 | 161 | absent |
| china-house | 143 | absent |
| habibs-cuisine | 178 | absent |
| hungry-howies | 116 | absent |
| jets-pizza | 60 | absent |
| marias-mexican-grill | 56 | absent |
| tru-pizza-co | 121 | absent |
| tru-pizza-co-ratings-20260812 | 20 | absent |

**The rewritten discovery and harvest path has never been executed end to end,
live or offline.** Every row of the validation checklist that needs a real page
remains genuinely open. The checklist is honest about this; it is only the
fixture-test line that overstates.

Separately, `DOORDASH_HARVEST_IMPLEMENTATION_PLAN.md:10` points at
`DOORDASH_HARVEST_COUNCIL_HANDOFF.md` for context and deliberation history. That
file is not in the project.

## Against the plan's "Done when"

One saved harvest file, without terminal logs, would let a reviewer determine:

| Criterion | Status |
| --- | --- |
| the source store/request | Met — `source_url`, `store_id`, tab identity verified before harvest |
| how discovery ended and whether it was sufficient | Met in code (`stop_reason`, `scroll_trace`, `page_usable`), except the browser-loss case (finding 2), which produces no file at all |
| what items and category memberships were observed | Met — `sections` collected and preserved through the parser |
| which captures succeeded, failed, retried, or were limited | Partly — retry evidence is misleading (finding 3) |
| whether successful payloads were structurally usable | Met — identity and shape validated before acceptance |
| why `complete` is or is not true | Met — `reasons[]` is derived, specific, and conservative |

## Harness

The rebuttal correctly objected that the 28-of-30 result was not reproducible,
because the harness lived in a session-scoped temp directory. It has been
preserved in the repository at:

```
external-data/scripts/check_doordash_harvest_safeguards.py
```

It now creates its own temp directory and runs standalone:

```
.venv/bin/python external-data/scripts/check_doordash_harvest_safeguards.py
# 28/30 checks passed
```

**Two checks fail by design** — they are the executable demonstrations of
findings 2 and 3, and should stay red until those defects are fixed. This file
is scratch-quality and is *not* the regression suite; converting it is Step 2 of
the next-steps plan, which also adds the parser-to-normalizer coverage this
harness omits.
