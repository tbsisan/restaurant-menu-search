# Details: Restaurant Menu Search

Use this file for working product, strategy, pilot, and implementation decisions that are more specific than `brief.md` but more stable than raw brainstorming in `workshop_log.md`.

---

## Details summary
- Current stage: concept
- Last updated: 2026-06-09
- Confidence level: low-to-medium

## Product decisions

### Core product choices
- **Status:** Tentative
- The product is a dish-level local menu search engine, not a restaurant-first directory.
- The first experience should emphasize finding a specific dish nearby, then helping the user place a pickup order.
- The strongest early product hook is likely some combination of better menu searchability and lower effective prices than delivery-app ordering, but the dominant wedge is still open.

### User and value assumptions
- **Status:** Tentative
- Early users are likely people who know what dish they want and are flexible about which nearby restaurant they choose.
- Price-sensitive pickup customers are likely an important early segment.
- Food explorers may also care about dish-level search, ratings, and review summaries.

## Pilot decisions

### Pilot shape
- **Status:** Tentative
- Geography: geography-first pilot centered around Southgate, Michigan.
- Segment: general local restaurant searchers and pickup customers.
- Cuisine scope: worth considering initial cuisine limits, but not decided yet.
- Success criteria: prove that users value dish-level search enough to use it repeatedly and that menu/order data can be kept accurate enough for trustworthy results.

### Rollout plan
- **Status:** Tentative
- Phase 1: small local region around Southgate.
- Phase 2: expand to the broader Metro Detroit region.
- Phase 3: consider wider regional or national expansion if the workflow and data quality hold up.

## Workflow and ops decisions

### User flow
- **Status:** Tentative
- Search flow: user searches for a specific dish and compares nearby matching results.
- Ordering flow: user selects a result and the system helps place a pickup order.
- Fulfillment flow: pickup is the default v1 assumption, but delivery may be viable later or in parallel because delivery APIs/providers exist.
- Payment flow: v1 default is pay at pickup rather than paying through the product.
- Failure handling: if a dish is unavailable, the price differs, or the restaurant refuses AI-agent ordering, contact the user by text message and resolve the issue with them.

### Human-in-the-loop / automation
- **Status:** Tentative
- Early versions should assume human-in-the-loop or constrained automation for order placement and exception handling.
- Fully autonomous phone ordering should not be assumed until the workflow is proven reliable.

## Data-source decisions

### Restaurant discovery sources
- **Status:** Tentative
- OpenStreetMap is attractive as a free source for nearby restaurant discovery.
- Google Maps / Google Places data may be more current, but cost and usage constraints need evaluation.
- Third-party services that depend on Google-backed data may also be relevant, depending on cost and freshness.

### Menu and ordering sources
- **Status:** Tentative
- We should include restaurant websites plus major delivery/order platforms and ordering providers.
- Target source categories should include apps/platforms such as DoorDash, Grubhub, Uber Eats, and similar services where available.
- Target ordering-site/infrastructure providers should include systems such as Clover and other restaurant ordering pages/embedded ordering flows.
- We likely need a source-priority system, probably favoring the restaurant's own site when it is clear and current, while cross-checking against third-party sources when needed.
- The scraper will need to handle text/HTML menus and OCR for image-based menus.
- We should also track delivery-enablement options such as DoorDash Drive, Uber Direct, Nash, Shipday, and similar delivery APIs/providers, since those could enable delivery without requiring us to build our own courier network.

### Ratings and reviews sources
- **Status:** Tentative
- We want to scrape restaurant ratings from sources such as Google, Yelp, TripAdvisor, DoorDash, and similar sites where feasible.
- We may want to aggregate those ratings into a composite restaurant view, though the aggregation method is still open.
- We may also want to gather customer reviews and generate an AI review summary.
- If platforms like DoorDash expose dish-level ratings or dish-specific review signals, we should try to capture those as well.

## Build and implementation notes

### Data and normalization requirements
- **Status:** Tentative
- Dish names will need normalization and alias handling, for example mapping similar labels like "veggie tacos" and "vegetarian tacos."
- Search quality will likely depend on storing multiple names, ingredients, and possibly preparation/style variants for a dish.
- We will likely need source confidence, freshness, and provenance fields for menu items, prices, ratings, and reviews.

### Known gotchas
- **Status:** Tentative
- "Build your own" or highly configurable dishes may be hard to represent cleanly.
- Add-ons, options, and substitutions may affect price in ways that are difficult to scrape and normalize.
- Menu pricing details may not appear right next to the dish listing.
- Aggressive scraping of third-party menu sources could create reliability, blocking, or policy issues, so request pacing and source strategy matter.

### Schema / design follow-ups
- **Status:** Open
- Decide how to model canonical dishes, aliases, ingredients, and configurable options.
- Decide how to store ratings and reviews from multiple providers, including whether to preserve raw provider-specific scores alongside any aggregate score.
- Decide how to represent dish-level review/ratings data when only some providers expose it.
- Decide how to model source priority and conflict resolution when sources disagree on names, prices, or availability.

## Known objections and current rebuttals

### Voice-agent legal/regulatory risk
- **Status:** Working assumption
- Current view: this is a low-priority risk for the first pilot.
- Rationale: voice agents are already in active commercial use, including in restaurant ordering contexts, which suggests meaningful near-term restrictions are unlikely to be the main blocker for a small pilot.
- Additional reasoning: the economic incentive for labor-saving automation appears strong, and there has not been obvious broad public backlash against interacting with voice agents for simple service workflows.
- Caveat: we should still avoid assuming zero legal/compliance work forever, but this concern should not currently block moving the project forward.

### Speech recognition / phone-ordering reliability
- **Status:** Working assumption
- Current view: this is a manageable operational risk rather than a project-threatening objection.
- Rationale: restaurant phone ordering already includes repetition, clarification, handling bad connections, and noisy communication for human callers; the relevant standard is whether the workflow can recover from misunderstandings, not whether every exchange is perfectly understood on the first try.
- Mitigation direction: allow repeats, confirmations, constrained ordering flows, and human fallback / intervention for exceptions.
- Caveat: this should still be tested in practice, especially for noisy environments, accents, and edge cases.

### Menu freshness and update frequency
- **Status:** Working assumption
- Current view: this is a real but manageable data-quality issue, not a likely fatal flaw.
- Rationale: many restaurants keep core menus relatively stable for long periods, often changing them infrequently because menu updates create operational and marketing friction. Deletions (can be problematic) are less common than additions (very low impact). Even if a menu item is deleted a restaurant may still be able to make the item.
- Additional reasoning: removed items are often less commonly ordered than core staples, which lowers the practical impact of some menu drift.
- Mitigation direction: scrape on a recurring schedule, track freshness/provenance, cross-check sources when needed, and treat occasional mismatches as an exception-handling problem rather than proof the model fails.
- Caveat: this remains something to monitor because stale prices, specials, or temporary changes can still damage trust if they become frequent.

## Open decisions needing resolution
- Is the strongest wedge lower prices, better dish searchability, review intelligence, or some combination?
- Should the initial pilot stay geography-first only, or start with a narrower cuisine subset inside the target geography?
- Which sources are legally, operationally, and economically viable enough for a first pilot?
- How should rating aggregation and AI review summaries be presented so they help users without overstating confidence?
- When should delivery enter the product: only after pickup works well, or early via third-party delivery APIs/providers?

## Rejected options
- Full v1 in-app payment flow — rejected for now in favor of simpler pay-at-pickup operations.
- Fully autonomous ordering from day one — rejected for now because exception handling and restaurant variability are still too uncertain.
