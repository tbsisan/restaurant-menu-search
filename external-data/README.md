# External Data for Restaurant Menu Search

This directory contains external source data and derived external-data outputs for the restaurant-menu-search project.

Shared convention: `~/Projects/PROJECT_DATA_CONVENTIONS.md`.

## Layout

- `raw-untracked/` — raw external downloads. Git-ignored.
- `derived/` — small curated/reproducible outputs that may be tracked.
- `derived-untracked/` — large derived outputs or intermediates. Git-ignored.
- `scripts/` — scripts used to generate derived files.

## Current source data

### `raw-untracked/downriver.xml`

OpenStreetMap XML export for the Downriver-ish area, downloaded from OpenStreetMap/Overpass.

- Size: about 511 MiB
- Local-only by default because it is raw external data and large
- OSM data is made available under ODbL; preserve attribution if outputs are published

## Derived files intended to keep

Generated from `raw-untracked/downriver.xml`:

- `derived/downriver-restaurants.jsonl`
  - All OSM nodes/ways where `amenity` is exactly `restaurant` or `fast_food`, excluding records with `disused:amenity=restaurant|fast_food`.

- `derived/downriver-mexican-restaurants-reviewed.jsonl`
  - Deterministic extraction plus LLM-reviewed missing-cuisine additions.

## Local-only intermediate files

These are useful audit/regeneration artifacts, but they are intermediate working files and live in `derived-untracked/` by default:

- `derived-untracked/downriver-mexican-restaurants.jsonl`
  - Deterministic Mexican/Mexican-adjacent restaurant extraction from `downriver-restaurants.jsonl`.

- `derived-untracked/downriver-restaurants-missing-cuisine.jsonl`
  - Restaurant records where no `cuisine` tag is set.

- `derived-untracked/downriver-restaurants-missing-cuisine-names.txt`
  - Tab-separated review list of missing-cuisine restaurant names/URLs.

- `derived-untracked/downriver-missing-cuisine-llm-mexican-candidates.jsonl`
  - LLM-reviewed Mexican-looking candidates among missing-cuisine records.

- `derived-untracked/downriver-missing-cuisine-llm-mexican-missed-by-deterministic.jsonl`
  - Subset of LLM candidates missed by the deterministic extractor.

## Regeneration

From this project directory:

```
python3 external-data/scripts/extract_osm_restaurants.py
python3 external-data/scripts/extract_mexican_restaurants.py
```

The LLM-reviewed files were created by reviewing `downriver-restaurants-missing-cuisine-names.txt`; if regenerated, document any manual/LLM review decisions here.

## Tracking and backup notes

- `raw-untracked/` is ignored by git.
- `derived-untracked/` is ignored by git.
- Current files under `derived/` are the likely reusable end products: the normalized restaurant extract and the reviewed Mexican subset.
- Intermediate/audit files live under `derived-untracked/` even if small, to keep the tracked folder focused.
- The local pre-commit data-size hook rejects staged files under `external-data/derived/` above 10 MiB, so large derived outputs should move to `derived-untracked/` or use Git LFS/DVC if they must be versioned.
