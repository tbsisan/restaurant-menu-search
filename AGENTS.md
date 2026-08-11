# Project Instructions

## Path Style

Prefer `~` over hard-coded full home paths in user-facing messages, for example `~/Projects/restaurant-menu-search`.

## Restaurant Scraping Spikes

Use Camofox with `humanize=True` for marketplace, search, map, and other dynamic or anti-bot restaurant sources, including Google Search, Google Maps, DoorDash, Grubhub, Uber Eats, Yelp, TripAdvisor, and similar sites.

Do not rely on plain `curl`/static HTML checks to decide whether a restaurant has a usable listing on those sources. `curl` is fine for official restaurant websites or simple static pages, but marketplace/listing verification should use the Camofox workflow learned from the prior DoorDash spike.

For dynamic marketplace/review sources, do not use `curl` results as evidence that review/menu/rating data is missing. Delivery and review sites often render with JavaScript, hide data behind interactions, or expose data in browser-loaded structured payloads such as `application/ld+json`; use Camofox page navigation/evaluation and inspect embedded JSON-LD or browser state before falling back to HTML text parsing.

Launch Camofox with the prior spike pattern: `Camoufox(headless=not args.headful, humanize=True)`. Set browser context geolocation for the target restaurant/local area, along with `locale="en-US"`, `timezone_id="America/Detroit"`, and `permissions=["geolocation"]`.

Use Google's restaurant side panel/order flow as a discovery source for online ordering providers. Search for the restaurant in Google with local geolocation enabled, inspect the side panel, and use the "Order online", "Order pickup", "Order delivery", or similarly labeled button/surface when present. Capture the ordering providers shown there; this can reveal most or all online ordering platforms associated with the restaurant.

When a spike includes the restaurant's own website, navigate beyond the homepage when useful. Save pages that contain restaurant information, menu data, ordering links, hours, about text, location/contact details, or other useful metadata. Save HTML when it is reasonably sized, and always save extracted plain text for these pages.

For spike tests, capture enough evidence to inspect later: resolved URL, HTML or structured response where available, screenshot/snapshot, extracted plain text, and a short notes/eval JSON describing whether the source was found and whether menu data looked parseable.

## Large HTML Files

Do not dump large HTML files into chat/tool output. Before inspecting saved marketplace or restaurant HTML, check file size or line lengths when there is any chance the file is large, minified, or rendered as huge single lines.

Prefer structured extraction over raw output:

- Use parsers such as BeautifulSoup, Playwright locators, or short purpose-built scripts to extract only relevant fields.
- For shell searches, use bounded output such as `rg -o`, `rg -m`, `head`, `sed` on known small text files, or narrowly targeted patterns.
- Avoid broad `rg` patterns against large HTML unless output is constrained to small snippets.
- Do not `cat`, `sed`, or unrestricted `rg` full marketplace HTML into the conversation.
- Save raw HTML as an artifact, then inspect summaries, counts, selected attributes, JSON-LD keys, or short snippets.

For menu scraper discovery, start with targeted selectors and domain terms instead of broad framework probes. Examples: `data-testid`, `menu-item`, `item-price`, `item-description`, known dish names from visible text, `application/ld+json`, `MenuItem`, and `hasMenuSection`.

When discovering how a large HTML page is structured:

- Prefer pretty-printing or parsing the HTML first so inspection happens in small navigable chunks instead of single giant lines.
- Search for a narrow term, then inspect a bounded neighborhood before and after the match. Keep the neighborhood small and increase only if needed.
- Use Python HTML parsers such as BeautifulSoup or lxml to find candidate nodes, then print only selected attributes, tag names, short outer HTML snippets, or `get_text()`/innerText for those nodes.
- Use browser DOM APIs or Playwright locators to inspect candidate elements directly from the rendered page when that is clearer than static HTML.
- In headful Camofox runs, use browser inspect/devtools when useful to identify selectors, attributes, and DOM hierarchy without sending the entire HTML through the agent context.
- Prefer iterating with small scripts that report counts and examples, for example: number of matching nodes, first 5 item titles/prices/descriptions, nearest section heading, and a short parent snippet.
