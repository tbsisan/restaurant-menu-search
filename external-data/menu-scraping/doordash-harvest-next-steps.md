# DoorDash harvest: implementation plan

**Revised 2026-08-14** after `doordash-harvest-code-review-rebuttal-2026-08-14.md`.
This is the version to implement against. It supersedes the first draft.

Companion documents:

- `doordash-harvest-code-review-2026-08-14.md` — the findings, with `file:line`
- `doordash-harvest-code-review-rebuttal-2026-08-14.md` — the author's response
- `doordash-harvest-validation-checklist.md` — the live-validation criteria
- `../scripts/check_doordash_harvest_safeguards.py` — the review harness

## What was settled by the rebuttal

The rebuttal accepts every substantive finding. Three things changed as a result
and are already reflected below, so do not re-litigate them:

1. **Commit sequencing.** The first draft opened with "commit a baseline first."
   The rebuttal objected to putting known defects on `main`, which is right.
   Revised: take a **WIP safety commit on a working branch** purely so ~1200
   lines of uncommitted work cannot be lost, then fix, then commit in coherent
   units. The branch is currently `main`, so create one first.
2. **The normalizer was missing from review scope.** It has now been reviewed
   and produced a new finding (Task 2e). Its lineage-preservation logic is
   correct; its counters are not.
3. **The harness is preserved.** It is in the repo and runnable. Task 1 converts
   it rather than recovering it.

One qualification the rebuttal makes that you should honour: `--items-file`
returning `incomplete` is **deliberate policy, not a bug**. See Task 4.

## Task 0 — Protect the work (5 minutes)

```
git checkout -b doordash-harvest-contract
git add external-data/scripts/ external-data/menu-scraping/*.md
git commit -m "WIP: DoorDash harvest contract rewrite (known defects, see review)"
```

This is a safety net, not a deliverable. Do **not** merge it to `main`. Final
commits come after Task 2, in reviewable units: the spike rewrite, the
parser/normalizer consumer changes, the tests, and the docs.

The large untracked research trees (`google-results-link-eval/batch/**`,
`canonical_openrouter/**`, the Grubhub scroll-step HTML dumps) are out of scope
here — most look like reproducible outputs wanting a `.gitignore` entry, but
that is a separate decision. Do not sweep them into this branch.

## Task 1 — Convert the harness into a regression suite

Highest-value task. It closes the one false claim, and it is the cheapest way to
validate most of the checklist without touching a live page or risking a bot
check.

Create `external-data/scripts/test_doordash_harvest.py`. Plain `pytest`; if you
would rather add no dependency, keep the assert-and-report shape the harness
already uses. Delete `check_doordash_harvest_safeguards.py` once its content has
moved.

**Port these, which the harness already covers and which pass today:**

- all eleven `fetch_item_page` branches;
- `build_harvest_status` gating: capped discovery, `--limit`, `--items-file`,
  empty selection, failures, pending captures, and the clean-run `complete` case;
- discovery outcomes: no-scroll menu → `bottom_stable`; bot-check page →
  `page_problem_signaled`; still-growing menu at cap → `scroll_limit_reached`;
- resume refusal on store-id, store-url, selection, and pre-contract mismatch;
- `in_progress` discovery sidecars never reused;
- `upsert_capture_result` not letting a failure clobber a success.

**Keep these two red until Task 2 fixes them** — they are the executable proof of
findings 2 and 3:

- `retryable diagnostics are all actually retried by cmd_harvest`
- `browser loss during discovery is handled`

**Add what the harness does not cover:**

- **A real payload fixture.** The success path is currently tested against a
  hand-built stub. Trim one real `itemPage` out of
  `doordash_spike/china-1-itempage-harvest.json` — the notes describe it as a
  compact bilingual store with 154 real option groups and no cross-sell noise —
  and assert against DoorDash's actual shape.
- **Parser → normalizer end to end** (the rebuttal's request, and where finding
  6 was found). Assert that a cross-listed size family survives both stages with
  `source_item_ids` intact and the union of `section_memberships` preserved.
  This reproduces it:

  ```
  harvest: 2 items, both sections ["Pizza", "Most Ordered"],
           titles "Cheese Pizza (Small)" / "Cheese Pizza (Large)"
  parse  → 2 sections, 2 unique items, 4 category placements
  normalize → "Cheese Pizza" under both sections,
              source_item_ids ["1","2"], memberships ["Pizza","Most Ordered"]
  ```

- **The `--ratings` merge**, once Task 2c is done.

## Task 2 — Fix the five defects

Each is small and independent. Task 1's tests should go green as you land them.

### 2a. Handle browser loss during discovery — HIGH

`spike_doordash_network_capture.py:698-811` (`collect_items`)

Give discovery the same treatment the item-capture loop already has. Every
`client.evaluate` call in `collect_items`, `discovery_page_state`, and
`wait_for_initial_menu_render` can raise `requests.RequestException` when the tab
dies; today that escapes as an uncaught traceback and the run produces **no
discovery record and no harvest file at all**.

Convert it into a returned discovery record with
`stop_reason: "browser_lost_during_discovery"`, carrying whatever items were
accumulated. The caller then writes a normal `incomplete` harvest.

Two details the rebuttal specifically asks for:

- Preserve items collected so far, not just the count.
- Write the `in_progress` sidecar on the way out **even when zero batches had
  checkpointed** — today the sidecar exists only if a batch already fired, which
  is the conditional behaviour that made the checklist's row-5 claim untrue.

### 2b. Make `retryable` mean something — MEDIUM

`spike_doordash_network_capture.py:1214-1220`, `:1244-1250`, `:1464`

Honour the flag, and record the evidence. Both documents agree on the shape:

- Retry any diagnostic carrying `retryable: true`.
- **Keep tab recovery exclusive to the `camofox_evaluate_*` kinds.** An ordinary
  network or HTTP retry must reuse the already-verified current tab — do not
  call `recover_tab` for a 503.
- Record an explicit `attempts: N` in the persisted diagnostic so the artifact
  states the count instead of leaving it inferred.

**One caution neither document raised, and it matters here.** Do not fast-retry
a **429**. This project's whole posture is human pacing, no evasion, and stop on
bot check; hammering a rate-limit response contradicts that and risks the exact
outcome the checklist tells you to avoid. Treat 429 as either a long backoff
(well beyond `Pacer`'s normal gaps) or a clean stop with the partial harvest
written and a `rate_limited` reason recorded. 408 and 5xx are the genuinely
safe fast retries. If you are unsure, stopping is the correct default — an
interrupted run is useful evidence, not a failure.

### 2c. Stop `--ratings` erasing inline ratings — MEDIUM

`parse_doordash_itempage.py:313-316`

The merge is unconditional, so it inserts `None` for any item the supplemental
file does not list, destroying card ratings the harvest already holds.
Demonstrated: an item at `92 / 48` came out `null / null`.

Apply the precedence rule the rebuttal proposes — a matching, non-null
supplemental rating may replace the inline value; a missing or null record must
never erase existing data:

```python
for entry in entries:
    rating = ratings_by_id.get(entry.get("item_id"))
    if rating and rating.get("like_percent") is not None:
        entry["like_percent"] = rating["like_percent"]
        entry["like_review_count"] = rating.get("like_review_count")
```

Write that rule into the function's docstring. Note that `parse_item:277` uses
`if "like_percent" in entry` to distinguish absent from null — that care is what
the current merge undoes, so preserve it.

### 2d. Sample by `sections`, not `section` — MEDIUM

`spike_doordash_network_capture.py:1401`

Bucket each item into **every** membership in `sections`, then deduplicate the
final selection by item ID so a cross-listed item is never fetched twice. This
is the last place collection order still decides structure, which plan priority
3 forbids.

### 2e. Fix the normalizer's placement-vs-item counters — MEDIUM

`normalize_menu_sizes.py:331-356` *(new finding; see review finding 6)*

The merged output is correct. The counters are not: because the parser now emits
one item per category it appeared in, the normalizer counts placements. A single
two-variant cross-listed family reports `size_items_merged: 2`; two source items
with menu codes report `menu_codes_extracted: 4`.

Make the normalizer report the same units the parser now does — distinguish
unique items from category placements in both `source.normalization` and the
printed summary. Deduplicate counters by `source_item_id` /
`source_item_ids` where an item is countable.

Then add a line to `doordash-menu-scraping-notes.md` recording that the China
House and China 1 figures ("113 of the 143 titles had a leading code", "the run
normalized 17 display titles") predate duplicate-category emission, so re-running
those stores yields larger numbers. Without that note it will read as a
regression to whoever checks next.

### 2f. Minor cleanups — LOW

- Progress counter mismatch: success lines print `[{i}/{len(items)}]` (`:1521`),
  failure and recovery lines print `[{i}/{len(fetch_order)}]` (`:1502`, `:1466`).
  On a resumed run these denominators disagree.
- `cmd_items:1313` uses `it["section"]` directly (KeyError-prone) after `:1312`
  used the safe `.get()`, and tallies by `section` only, so the printed tally
  disagrees with the `sections` data it just wrote.

## Task 3 — Correct the checklist's false claim

Once Task 1 lands, edit `doordash-harvest-validation-checklist.md:17`. It
currently reads "Fixture tests already cover these branches." Make it name the
actual suite, so the claim becomes verifiable rather than aspirational.

While there, restate row 5 ("Browser loss during discovery") against the
behaviour Task 2a actually delivers.

## Task 4 — Document the `--items-file` policy

The rebuttal is right that this is deliberate conservatism, not an accident: a
bare items file carries no evidence about how or where its list was discovered,
so it cannot support a completeness claim.

**Do this now (cheap):** write the policy into the checklist and into
`cmd_harvest`'s `--items-file` help text — a bare items file is a development
convenience and always yields `state: "incomplete"`.

**Defer this (only if the two-phase workflow is still wanted):** have `cmd_items`
write the same discovery sidecar `cmd_harvest` writes, and let `--items-file`
accept that sidecar instead of a bare array, verifying store ID, canonical URL,
selector contract, and `discovery.status == "complete"` before allowing a
complete harvest. Do not build this speculatively.

## Task 5 — Live validation, last

Do not start here. Every live run risks a bot check, and Tasks 1–2 find cheaper
bugs first. Work the checklist in this order:

1. **Small menu.** A store whose menu fits the viewport. Confirms `bottom_stable`
   without scrolling and produces the first real `schema_version: 2` artifact in
   the project.
2. **Large virtualized menu.** Validates checklist rows 2 and 8 together, and is
   the only way to exercise the widened selector contract.

   **Do this comparison, and treat it as a gate.** Collection previously used a
   single selector, `[data-testid="MenuItem"]`; it now uses all six of
   `MENU_CARD_SELECTORS` (`:42-49`), including `a[href*="?itemId="]`. Run against
   a store you already have a pre-contract harvest for — china-1 (161 items) or
   habibs (178) are the best candidates — and diff the item count. A materially
   different count means "complete" now means something different than it did for
   every existing harvest. Explain the difference before trusting any new
   artifact. Record the comparison in the notes either way.

   Note also what is *not* open here: the pre-contract harvests already prove
   async `evaluate` resolves Promises for `ITEMPAGE_FETCH_JS`. The genuinely
   unproven half of checklist row 8 is whether `window.scrollBy` drives the real
   menu scroll container.
3. **Duplicate-category item.** Already proven offline; live only needs to
   confirm a real recommendation shelf yields two `sections` entries.
4. **Delayed/stalled loading** and the two **browser-loss** rows. Hardest to
   stage, lowest marginal value once Tasks 1–2 land, since the fixtures cover the
   logic and only real-world triggering is unproven.

Keep the checklist's stop rule: **if a bot check appears, stop and leave the page
for manual handling.** An interrupted run is evidence, not an obstacle to work
around.

## Task 6 — Housekeeping

- The council handoff and implementation plan now live beside this document:
  `doordash-harvest-council-handoff.md` and
  `doordash-harvest-implementation-plan.md`.
- Keep the eight pre-contract harvests. They remain fully usable by the offline
  parser and they are the baseline for the Task 5.2 comparison.

## Definition of done

- `test_doordash_harvest.py` exists, covers the branches listed in Task 1, and
  passes fully.
- The five defects in Task 2 are fixed, each with a test that was red first.
- The checklist no longer claims coverage that does not exist.
- One live `schema_version: 2` artifact exists that satisfies the checklist's
  own success criterion: `complete: true`, `harvest.state: "complete"`,
  discovery `stop_reason: "bottom_stable"`, zero failed and pending captures,
  and equal selected and successful counts.
- The Task 5.2 item-count comparison against a pre-contract harvest is recorded
  in `doordash-menu-scraping-notes.md`, with an explanation if the counts differ.
