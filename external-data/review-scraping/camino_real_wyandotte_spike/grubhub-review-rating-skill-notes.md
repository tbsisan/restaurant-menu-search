# Grubhub Review/Rating Skill Notes

Target used for spike:

- Restaurant: Camino Real Mexican Grill
- Address: 3851 Fort St, Wyandotte, MI 48192
- Grubhub reviews URL: `https://www.grubhub.com/restaurant/camino-real-mexican-grill-3851-fort-st-wyandotte/6882728/reviews`

## Browser Setup

Use Camofox for Grubhub. Do not use `curl` as evidence that Grubhub review/rating data is missing; the useful page state is JavaScript-rendered and should be inspected in a browser context.

For this spike, Camofox was started with:

```bash
env CAMOFOX_HEADLESS=false CAMOFOX_HUMANIZE=true CAMOFOX_PORT=9379 ~/.local/bin/camofox-browser
```

Notes:

- Headed mode fell back to virtual display because no `DISPLAY` was available.
- `CAMOFOX_HUMANIZE=true` was enabled.
- Do not set `CAMOFOX_ALLOW_WEBGL=false` for normal restaurant scraping. Leave WebGL unset/enabled so Camofox can generate a plausible WebGL fingerprint; disabling WebGL may itself be suspicious to some WAFs.

Create a tab with local restaurant context:

- `locale`: `en-US`
- `timezoneId`: `America/Detroit`
- `geolocation`: `42.19351025, -83.1795100375`
- viewport used: `1365x900`

Confirm geolocation from inside the browser before relying on local search/provider behavior:

```js
async () => {
  const permission = await navigator.permissions.query({ name: "geolocation" }).then(p => p.state);
  const position = await new Promise(resolve =>
    navigator.geolocation.getCurrentPosition(
      p => resolve({
        latitude: p.coords.latitude,
        longitude: p.coords.longitude,
        accuracy: p.coords.accuracy
      }),
      e => resolve({ error: e.message, code: e.code }),
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 0 }
    )
  );
  return {
    permission,
    position,
    language: navigator.language,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
  };
}
```

Expected for this spike:

```json
{
  "permission": "granted",
  "position": {
    "latitude": 42.19351025,
    "longitude": -83.1795100375,
    "accuracy": 0
  },
  "language": "en-US",
  "timezone": "America/Detroit"
}
```

## Discovery

Google Search triggered an unusual-traffic interstitial during this spike. DuckDuckGo worked.

DuckDuckGo query:

```text
Camino Real Mexican Grill Wyandotte Grubhub
```

Useful results found:

- Main Grubhub listing: `https://www.grubhub.com/restaurant/camino-real-mexican-grill-3851-fort-st-wyandotte/6882728`
- Dedicated reviews page: `https://www.grubhub.com/restaurant/camino-real-mexican-grill-3851-fort-st-wyandotte/6882728/reviews`

Open the dedicated `/reviews` URL. If it doesn't show in results just append /reviews to the main listing URL.

## Review Summary Extraction

On the live Grubhub reviews page, inspect scripts for JSON-LD first:

```js
(() => {
  const scripts = Array.from(document.scripts).map((s, index) => ({
    index,
    id: s.id || "",
    type: s.type || "",
    src: s.src || "",
    text: s.textContent || ""
  }));

  const jsonld = scripts
    .filter(s => /ld\+json/i.test(s.type))
    .map(s => ({
      index: s.index,
      id: s.id,
      type: s.type,
      src: s.src,
      text: s.text.slice(0, 200000)
    }));

  return {
    url: location.href,
    title: document.title,
    scriptCount: scripts.length,
    jsonldCount: jsonld.length,
    jsonld
  };
})()
```

For Camino Real, Grubhub returned one `application/ld+json` script containing a Restaurant schema object:

```json
{
  "@context": "http://schema.org",
  "@type": "Restaurant",
  "@id": "https://www.grubhub.com/restaurant/camino-real-mexican-grill-3851-fort-st-wyandotte/6882728",
  "url": "https://www.grubhub.com/restaurant/camino-real-mexican-grill-3851-fort-st-wyandotte/6882728",
  "name": "Camino Real Mexican Grill",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "3851 Fort St",
    "addressLocality": "Wyandotte",
    "addressRegion": "MI",
    "postalCode": "48192",
    "addressCountry": "USA"
  },
  "geo": {
    "@type": "GeoCoordinates",
    "latitude": "42.19354248",
    "longitude": "-83.17951203"
  },
  "telephone": "7342588790",
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": "4.7",
    "ratingCount": "481",
    "worstRating": 0,
    "bestRating": 5,
    "reviewCount": 59
  },
  "priceRange": "$$$"
}
```

The summary values to extract are:

- Rating: `aggregateRating.ratingValue`
- Rating count: `aggregateRating.ratingCount`
- Review count: `aggregateRating.reviewCount`
- Best/worst rating: `aggregateRating.bestRating`, `aggregateRating.worstRating`
- Restaurant identity/address: `name`, `address`, `geo`, `telephone`, `url`

For this page:

```json
{
  "source": "grubhub",
  "rating": "4.7",
  "rating_count": "481",
  "review_count": 59,
  "best_rating": 5,
  "worst_rating": 0
}
```

## Individual Reviews

The JSON-LD on this Grubhub page did not include individual review bodies. The visible review rows were rendered into the page body.

Initial DOM text showed:

- Page heading: `Camino Real Mexican Grill Reviews`
- `481 ratings`
- `59 reviews`
- Sort control: `Most recent`
- Review rows with reviewer name, date, badge/reviewer count, star icons, review text, and sometimes ordered items.

Example rendered review fields visible in the accessibility snapshot:

- Reviewer: `Debbie`
- Date: `May 08, 2026`
- Text: `excellent!!! 5 star`
- Ordered items: `Tacos`, `Enchiladas Dinner`, `Churros`

For a future skill, use JSON-LD for aggregate rating/review count, then parse DOM-rendered review cards separately if individual reviews are needed.

## DOM Review Extraction

Grubhub review cards have stable test ids in the rendered DOM. After opening the reviews page, use Camofox `evaluate` to extract compact JSON from the DOM instead of ingesting the full HTML.

Useful selectors:

- Review card: `[data-testid="restaurant-review-item"]`
- Reviewer name: `[data-testid="review-reviewer-name"]`
- Review content: `[data-testid="review-content"]`
- Per-review rating stars: `[data-testid="starRating"] [data-testid="full-star"]`
- Ordered item pills: `button` elements inside each review card
- More reviews button: `button[data-testid="reviews-see-more"]`

The date did not have a stable test id in the inspected markup. Extract it from the card text with:

```js
/\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}\b/
```

Loading behavior observed:

- Initial loaded review cards: `35`
- Page summary: `481 ratings`, `59 reviews`
- Clicking `button[data-testid="reviews-see-more"]` once loaded more cards.
- Loaded cards after click: `58`
- After that, `reviews-see-more` disappeared and repeated scrolling did not add more cards.
- All 58 extracted cards had reviewer, date, rating, and review content.

The page summary still reported `59 reviews`, so record both the reported review count and the extracted card count. Treat a mismatch as a source limitation unless another pagination/control path is found.

Compact browser-side extraction shape:

```json
{
  "summary": {
    "ratingCount": 481,
    "reviewCount": 59
  },
  "loadedReviewCards": 58,
  "cards": [
    {
      "index": 1,
      "reviewer": "Debbie",
      "date": "May 08, 2026",
      "rating": 5,
      "content": "excellent!!! 5 star",
      "orderedItems": ["Tacos", "Enchiladas Dinner", "Churros"],
      "reviewerMeta": ["Top reviewer", "Debbie ordered:"]
    }
  ]
}
```
