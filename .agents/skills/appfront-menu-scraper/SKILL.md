---
name: appfront-menu-scraper
description: NOT YET IMPLEMENTED. Detection signature and navigation notes for restaurants using AppFront-powered online ordering (e.g. order.middleeats.com), so a future menu-discovery pass can recognize an AppFront site and dispatch a real appfront-menu-scraper (and appfront-reviews-scraper, once reviews are investigated). Read this before building either.
---

# AppFront Menu Scraper (notes only, not built yet)

## Why this exists

Menu discovery needs to recognize when a restaurant's ordering site is
running on AppFront so it can dispatch the right scraper, the same way it
would recognize DoorDash/Grubhub/Uber Eats/Toast/Square/Cash App links.
AppFront is white-labeled per business onto the restaurant's own domain
(e.g. `order.middleeats.com`), not a shared domain like `doordash.com`, so
domain-pattern matching alone won't catch it. This doc exists so that
detection heuristic isn't rediscovered from scratch later, and so the actual
scraper skill has a head start on navigation and item markup once it's built.

Confirmed against `https://order.middleeats.com/a` (Middle Eats).

## Detecting an AppFront site

Either signal below is reliable and doesn't depend on the restaurant's
custom domain:

1. A `<meta>` tag whose `content` contains `.appfront.app`, e.g.
   `<meta property="og:url" content="https://middleeats.appfront.app/">`.
   This is present even though the page is served from the custom domain.
2. A footer "Powered by" badge: `<a href="https://appfront.ai/?src=pwrdby">`
   wrapping a `[class*="PoweredBy"]` element with an AppFront logo SVG (no
   accessible text on the SVG itself, so match the link href, not visible
   text).

Don't rely on the `index-module--*--<hash>` CSS module class names for
detection or scraping selectors beyond a single confirmed session - they're
webpack content hashes and may not be stable across AppFront deployments.

## Navigation to the actual menu

Google results for an AppFront restaurant did not surface a direct menu
link. The homepage requires a multi-step flow to reach a specific location's
menu - and a location must be picked because a business can have several
branches:

1. Homepage → click "Start New Order" → navigates to `/serving-options/`.
2. Click "Pickup" (or "Delivery") → navigates to
   `/find-location/?servingOptionType=pickup`.
3. This page lists every branch sorted by distance from the browser's
   geolocation, as plain `<a href="/order/?branchId=<id>&branchName=<name>&servingOptionType=pickup">`
   links - no need to click each one, just read the `href` list directly and
   pick (or iterate) the branch(es) you want by `branchName`.
4. Load that `/order/?branchId=...` URL directly for the target branch's
   menu. It's a normal navigable URL, not a modal/SPA state that requires
   replaying the click sequence every time - once you know the `branchId`,
   you can jump straight there on future scrapes.

## Menu page structure (confirmed on the Southgate branch)

- Category headings are plain `h2`/`h3` text (e.g. "Best Sellers", "Bowls",
  "Wraps", "Salads", "Specialties", "Sides", "Desserts", "Sauces and
  Dressings", "Extras", "Smoothies*", "Fountain Drinks").
- A "Best Sellers" category exists, same duplicate-rollup pattern as Uber
  Eats' carousel / DoorDash's "Most Ordered" / Grubhub's "Best Sellers" -
  check whether its items reuse the same durable id as their real-category
  copy before assuming name-matching is needed (established pattern: it
  usually doesn't need to be name-matched, Grubhub and DoorDash both reuse
  the same id/card).
- Item cards: `div[role="button"][aria-label="<item name>"]` with classes
  `index-module--ListCard--b1bd3 index-module--CategoryItem--6348b` (class
  hash may not be stable - prefer `[role="button"][aria-label]` inside the
  menu area as the durable selector).
  - Name: `aria-label` attribute, or `.index-module--ListCardTitle--a9e35 strong`.
  - Price: sibling `<span>` in the same title row as the name.
  - Description: `.index-module--ListCardDescription--8316d` (may be
    truncated with "..." in the DOM - check for a full-text source, e.g. an
    item detail modal, before assuming the truncated text is complete).
- ~100 item cards were already mounted without scrolling on the Southgate
  branch; unconfirmed whether larger menus lazy-load/virtualize like
  DoorDash/Grubhub/Square do.

## Not yet investigated

- Whether/how sold-out items are marked (see
  `external-data/menu-scraping/sold-out-detection-notes.md` for the general
  approach and other platforms' signals once this becomes relevant).
- Whether the site exposes reviews/ratings anywhere (needed before an
  `appfront-reviews-scraper` skill can be scoped).
- Whether the truncated item descriptions have a full-text source (e.g. a
  click-to-expand modal).
- Full-menu scroll/virtualization behavior on a larger menu than Middle
  Eats' ~100 items.
