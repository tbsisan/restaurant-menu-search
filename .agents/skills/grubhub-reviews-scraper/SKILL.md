---
name: grubhub-reviews-scraper
description: Scrape restaurant reviews from Grubhub into compact structured JSON. Use when Codex/Antigravity/Hermes/OpenCode/etc needs to collect Grubhub restaurant review cards, review text, reviewer/date/rating fields, and aggregate rating/review counts for the restaurant-menu project
---

# Grubhub Reviews Scraper

## Overview

Use this skill to capture Grubhub restaurant reviews from rendered in-browser pages. The primary goal is individual review extraction; aggregate rating fields are useful side effects and should be captured when available.

Use Camofox and the camofox skill to inspect the rendered browser DOM and extract the reviews.

## Output Layout

Store restaurant review data under the restaurant directory:

```text
external-data/restaurants/<restaurant-name>/reviews/
```

Write the final compact JSON as:

```text
external-data/restaurants/<restaurant-name>/reviews/grubhub-reviews-<restaurant-name>.json
```

Write intermediates and raw files under:

```text
external-data/restaurants/<restaurant-name>/reviews/raw/
```

Use the project's existing restaurant slug if one exists. Otherwise derive `<restaurant-name>` as lowercase hyphen-case from the restaurant name.

## Workflow

1. Start Camaofox. Set local browser context for the target restaurant:
   - `locale="en-US"`
   - target-area `timezone_id` or `timezoneId`
   - target-area `geolocation`
   - geolocation permission enabled
2. Verify geolocation from inside the browser before scraping if local search/discovery is involved.
3. Search <restaurant-name> city grubhub in google. If google fails, use duckduckgo. If duckduckgo fails try bing. If all fail then stop. Exit the skill and report the problem. Never try curl.
4. Find the concrete restaurant reviews URL:
   - Prefer a known Grubhub restaurant URL with ending in `/reviews`.
   - If the reviews url is not surface in search results find the main Grubhub link and append /reviews yourself.
5. On the live reviews page, extract JSON-LD first for restaurant identity and aggregate counts. and save in the raw files directory.
6. Click `button[data-testid="reviews-see-more"]` and scroll until the button disappears and the review-card count stops increasing.
7. Extract individual review cards from the rendered DOM into compact JSON and save as the final extraction.


## Review Card Extraction

Use these rendered DOM selectors:

```text
review card:      [data-testid="restaurant-review-item"]
reviewer name:   [data-testid="review-reviewer-name"]
review content:  [data-testid="review-content"]
rating stars:    [data-testid="starRating"] [data-testid="full-star"]
more reviews:    button[data-testid="reviews-see-more"]
```

Dates may not have a stable test id. Extract them from each card's text:

```js
const dateRe = /\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}\b/;
```

Ordered items are usually `button` elements inside the review card. Strip trailing UI text such as `Plus icon`.

## Compact JSON Shape

Final JSON should be compact and source-specific:

```json
{
  "source": "grubhub",
  "source_url": "https://www.grubhub.com/restaurant/.../reviews",
  "restaurant": {
    "name": "Restaurant Name",
    "address": {},
    "telephone": null,
    "geo": null
  },
  "aggregate": {
    "rating": null,
    "rating_count": null,
    "review_count": null,
    "best_rating": null,
    "worst_rating": null
  },
  "extraction": {
    "loaded_review_cards": 0,
    "reported_review_count": null,
    "loaded_all_reported_reviews": false,
    "notes": []
  },
  "reviews": [
    {
      "index": 1,
      "reviewer": "Reviewer Name",
      "date": "Jan 01, 2026",
      "rating": 5,
      "content": "Review text",
      "ordered_items": [],
      "reviewer_meta": []
    }
  ]
}
```

If the page reports more reviews than are extractable after all visible controls are exhausted, keep the extracted cards and add a note in `extraction.notes`.

## Raw Artifacts

Save useful raw evidence under `reviews/raw/<restaurant-name>/`:

- JSON-LD evaluation response
- review-card extraction response
- Camofox accessibility snapshot or screenshot when helpful
- short run notes with URL, geolocation, button-click history, and card counts

Avoid saving full HTML unless debugging selectors; it is usually much larger than needed and should not be the primary extraction artifact.

## Pitfalls

- A Grubhub static shell page is not useful. Recapture with Camofox.
- The reviews URL can be discovered directly or by appending `/reviews` to a concrete restaurant URL.
- The page may report a larger `reviewCount` than the rendered cards available after `See more` disappears; record the mismatch instead of fabricating missing reviews.
- Accessibility snapshots are useful for inspection, but final extraction should come from DOM selectors via Camofox `evaluate`.
