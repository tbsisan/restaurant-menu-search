# Response to the DoorDash harvest code review

**Date:** 2026-08-14

**Responding to:** `doordash-harvest-code-review-2026-08-14.md` and
`doordash-harvest-next-steps.md`

## Overall assessment

The review is strong and mostly fair. Its central verdict is correct: the
harvest-contract redesign is substantially implemented and mostly behaves as
intended, but the evidence supporting it was overstated.

In particular, the distinction between code that was exercised temporarily and
regression tests preserved in the repository is important. The implementation
has received meaningful offline testing, but it has not yet received durable,
repeatable fixture coverage or live end-to-end validation against the current
DoorDash interface.

## Findings accepted

### The fixture-test statement was incorrect

The validation checklist says that fixture tests already cover the bad
`itemPage` response branches. That is not accurate. Those branches were
exercised with temporary scripts, but the tests were not saved in the
repository. The checklist should not claim persistent fixture coverage until a
real regression suite is added.

### Browser loss during discovery is not handled safely

This is a genuine high-priority defect. `collect_items` does not catch failures
from its Camofox `evaluate` calls. A browser or tab failure can therefore escape
as an exception before the caller receives a final discovery record or writes a
harvest artifact.

An `in_progress` discovery sidecar may exist if at least one earlier batch
triggered a checkpoint, but that is conditional and does not satisfy the
checklist's stronger claim. Discovery should return an explicit incomplete
result and preserve the items accumulated so far, including when failure occurs
before the first batch checkpoint.

### Retry metadata and retry behavior disagree

`network_fetch_error` and transient HTTP responses such as 408, 429, and 5xx
are marked `retryable: true`, but the harvest loop currently retries only
Camofox evaluation failures. This is misleading evidence even if `retryable`
is interpreted as eligibility rather than proof that a retry occurred.

The scraper should honor the flag where safe and record an explicit attempt
count. Browser recovery should remain limited to browser-control failures;
ordinary network or HTTP retries should reuse the verified current tab.

### Supplemental ratings can erase inline ratings

The `--ratings` merge currently inserts rating keys for every item and uses
`null` when the supplemental file lacks a matching record. This can overwrite
valid card ratings already stored in the harvest.

The precedence rule should be explicit. A reasonable rule is that a matching,
non-null supplemental rating may replace the inline value, while a missing or
null supplemental record must not erase existing data.

### Section sampling still depends on the legacy primary section

The main discovery and parser paths preserve every category membership, but
`--sample-per-section` still buckets items using only the first-observed
`section`. That makes sampling dependent on collection order and prevents
recommendation or cross-listing sections from being represented correctly.

Sampling should consider every entry in `sections`, then deduplicate the final
item selection by item ID so a cross-listed item is never fetched twice.

### The minor findings are valid

The inconsistent progress denominators, unsafe `it["section"]` lookup, and
single-section `cmd_items` tally are real and inexpensive to correct.

## Findings that need qualification

### The lack of live validation was already acknowledged

It is correct that no saved harvest currently has the schema-v2 contract and
that the rewritten discovery path has not been exercised end to end against a
live DoorDash page. This is an important readiness limitation, but it was not
represented as completed work. It is the reason the operational validation
checklist was created.

The correct conclusion is that the implementation is not production-proven,
not that the code changes themselves are unsupported or fictitious.

### `--items-file` incompleteness is conservative policy, not clearly an accident

The current completeness rule deliberately requires an unbounded live
discovery. Therefore a bare `--items-file`, which carries no evidence about how
or where its item list was discovered, cannot claim a complete harvest.

That is defensible, but it needs to be documented as a deliberate policy. A
better eventual two-phase design would allow an items file to be accompanied by
a completed discovery sidecar whose store ID, canonical URL, selector contract,
and stop condition can be verified. Until that exists, treating a bare items
file as unverified is the safer behavior.

### A known-defective baseline should not be committed directly to `main`

The recommendation to preserve a baseline for reviewability is sensible, but
the current Git diff already provides that baseline. There is little value in
placing known defects into the main branch solely to create a historical
boundary.

A cleaner sequence is to add regression tests that expose the defects, fix the
defects, and then commit the result in bounded, reviewable units. A temporary
branch or local work-in-progress commit is reasonable if preservation is
needed, but it should not be confused with a finished project commit.

## Limitations in the review

### The test-file claim is too broad

The statement that no `test_*.py` or `*_test.py` file exists anywhere in the
project is literally false; at least one unrelated image-generation script has
such a suffix. This does not change the substantive finding: there is no
persistent DoorDash harvest regression suite.

### The declared file scope omits the normalization stage

The review's file list omits `normalize_menu_sizes.py`, even though that script
was changed to preserve `source_item_ids` and the union of
`section_memberships` when multiple size-specific items are merged.

The synthetic parser check proves that duplicate-category membership survives
capture and parsing, but it does not prove the complete parser-to-normalizer
pipeline. The permanent test suite should cover that final transformation as
well.

### The reported behavioral checks are not yet reproducible

The reported 28-of-30 result is useful evidence, but the harness is stored in a
temporary directory and the review does not enumerate all 30 assertions in a
form that can be rerun. The harness should be recovered promptly, reviewed, and
promoted into the repository before it disappears.

## Recommended order of work

1. Recover and preserve the temporary review harness if it still exists.
2. Convert its checks into persistent regression tests, initially retaining the
   failing cases that demonstrate the confirmed defects.
3. Fix discovery failure handling, retry behavior and attempt evidence, ratings
   precedence, multi-section sampling, and the minor reporting problems.
4. Add an end-to-end parser and normalizer fixture proving that source identity
   and duplicate-category memberships survive size normalization.
5. Decide and document the `--items-file` policy, preferably adding support for
   verified discovery evidence if the two-phase workflow remains useful.
6. Run the live validation checklist, stopping and leaving the page untouched
   if a bot check appears.
7. Commit the work in coherent batches after the known defects are resolved.

## Conclusion

The review should be treated as credible and actionable. It confirms that the
core redesign is real while identifying several defects that should be fixed
before live validation. Its principal recommendations are accepted, subject to
the qualifications about `--items-file`, commit sequencing, and its incomplete
review of the normalization stage.
