# DoorDash JSON-LD Workflow

## What Worked

The good Maria's Mexican Grill DoorDash output came from rendered-page JSON-LD:

1. Camofox rendered the DoorDash store page.
2. The page's `script[type="application/ld+json"]` scripts were extracted.
3. The extracted scripts were saved in a wrapper JSON file with `ok`, `result`, `resultType`, and `truncated`.
4. The parser converted the `@type: "Menu"` object into menu sections and menu items.

The accessibility snapshot was useful for evidence and reviews, but not the primary menu extraction source.

## Example Artifacts

Maria's:

- `external-data/menu-scraping/doordash_spike/marias-mexican-grill-doordash-jsonld-response.json`
- `external-data/menu-scraping/doordash_spike/marias-mexican-grill-doordash-parsed.json`

Camino Real:

- `external-data/menu-scraping/camino_real_wyandotte_spike/camino-real-wyandotte-doordash-jsonld-response.json`
- `external-data/menu-scraping/camino_real_wyandotte_spike/camino-real-wyandotte-doordash-parsed.json`
- `external-data/menu-scraping/camino_real_wyandotte_spike/doordash-menu.txt`

## JSON-LD Shape

Useful DoorDash pages usually expose scripts with these `@type` values:

- `Restaurant`
- `Organization`
- `Menu`
- `FAQPage`
- `BreadcrumbList`

The `Menu` script is the important one. It contains `hasMenuSection`, and each section contains `hasMenuItem`. Those values may be nested lists, so parsers should flatten lists recursively.

## Capture Requirements

Use Camofox with `humanize=True` and local context:

```python
with Camoufox(headless=not args.headful, humanize=True) as browser:
    context = browser.new_context(
        viewport={"width": 1365, "height": 900},
        locale="en-US",
        timezone_id="America/Detroit",
        geolocation={"latitude": target_lat, "longitude": target_lon},
        permissions=["geolocation"],
    )
```

Save:

- rendered HTML
- screenshot
- accessibility snapshot or visible text when useful
- JSON-LD response
- parsed JSON
- source-specific text menu

## Discovery

Google's restaurant side panel/order flow can expose provider URLs that normal search misses. Look for:

- Order online
- Order pickup
- Order delivery

Provider URLs may include:

- `https://custom.order.online/.../store/...`
- `https://www.doordash.com/en/store/...`
- Grubhub and Uber Eats URLs

Treat `custom.order.online` as DoorDash-backed for extraction purposes.
