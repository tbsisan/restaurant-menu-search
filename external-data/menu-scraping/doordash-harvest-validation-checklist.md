# DoorDash harvest validation checklist

The capture script now contains safeguards against incomplete discovery,
misidentified stores, stale browser state, malformed item-page data, and unsafe
resume. This checklist is the remaining operational validation needed before
treating it as production-ready: it proves that those safeguards match real
DoorDash and Camofox behavior.

| Check | What we are testing | Good result |
| --- | --- | --- |
| Small menu | A restaurant whose complete menu fits in the initial viewport. | Discovery reaches `bottom_stable`, finds items, and completes without needing a newly mounted batch. |
| Large menu | A long menu where DoorDash mounts and unmounts cards while scrolling. | The scroll trace shows item counts increasing in batches; discovery ends `bottom_stable`, not at its cap, and there are no missing or pending item captures. |
| Duplicate-category item | An item shown in its normal category and in a recommendation shelf such as `Most Ordered`. | The raw item has one ID and multiple `sections`; parsed output intentionally places it in both categories with the same `source_item_id`. |
| Delayed or stalled loading | A slower real page, for example through one of the slower proxies. | The scraper waits long enough and continues, or records an explicit incomplete reason. It must never claim `complete` without proving collection ended normally. |
| Browser loss during discovery | Camofox/browser disappears while cards are being collected. | The scraper checkpoints the observed cards (including an empty initial observation) as `in_progress`, returns `browser_lost_during_discovery`, and the caller writes a normal incomplete harvest. A partial sidecar is never reused as complete. |
| Browser loss during item capture | The browser disappears after some `itemPage` payloads have been saved. | The harvest retains successful items and its failure/pending evidence; a matching resumed run reuses only those validated successes. |
| Bad `itemPage` responses | HTTP, GraphQL, malformed, changed-shape, or mismatched-item conditions. | The affected item has a specific diagnostic such as `http_error`, `graphql_errors`, or `item_identity_mismatch`, rather than a vague missing result. `pytest external-data/scripts/test_doordash_harvest.py` covers these branches with a trimmed recorded `itemPage` fixture; a natural live failure is optional. |
| Camofox details | Whether async page evaluation waits correctly, text-selector clicking works, and `window.scrollBy` controls the real menu scroll container. | A large-menu trace proves that scrolling moves the page and loads cards. Rely on text-selector clicking only after observing it on an appropriate noncritical page state. |

## Normal full-scrape success criterion

A full harvest is entitled to claim success only when all of the following are
present in its artifact:

- top-level `complete: true`;
- `harvest.state: "complete"`;
- discovery `stop_reason: "bottom_stable"`;
- zero failed and pending item-page captures; and
- equal selected and successful item-page counts.

If a bot check appears during any live validation, stop and leave the page for
manual handling. An interrupted run is useful validation evidence; it is not a
condition to work around automatically.
