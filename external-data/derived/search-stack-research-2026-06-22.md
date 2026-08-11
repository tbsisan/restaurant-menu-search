# Restaurant Menu Search Stack Research

Source: AI Council conversations stored outside this repo:

- `~/Projects/ai-council-plus/data/conversations/158accd2-fad9-4083-ab41-7b0dbcdcc41c.json`
- `~/Projects/ai-council-plus/data/conversations/4c2fd94e-bc6f-46d1-9e83-a63343e012f9.json`
- Indexed by `~/Projects/ai-council-plus/data/conversations/conversations_index.json` as `Restaurant Menu Search Stack`, created `2026-06-22T05:05:52.828744+00:00`.

## Original Question

The prompt asked what frontend/backend stack should power a local restaurant menu search site where roughly 1,000 restaurants and 50,000 menu items are searchable across restaurants. The product needs fast initial page load, snappy search, dish-name search, ingredient filtering, and likely either edge database queries or local in-browser databases.

## Core Finding

The council treated 50,000 menu items as a middle scale:

- Small for SQLite, Postgres, or a dedicated search engine.
- Large enough that blindly shipping full JSON on initial page load can hurt mobile users.
- Small enough that a compressed prebuilt browser search index is realistic.

The strongest final recommendation was a hybrid architecture:

1. Keep an edge or primary database as the source of truth.
2. Generate a prebuilt search index from that source.
3. Serve the index from a CDN/object store.
4. Cache it in the browser with IndexedDB.
5. Run search locally in a Web Worker for instant interactions.
6. Validate freshness in the background with an edge endpoint.

## Recommended Shape

The highest-ranked synthesis favored:

- Search: Orama in browser and edge worker.
- Browser persistence: IndexedDB.
- Runtime isolation: Web Worker for loading/querying the index.
- Delivery: Cloudflare R2 or similar CDN-backed static asset.
- Edge/backend: Cloudflare Workers plus D1 or Turso for source-of-truth/validation.
- Primary data store: Postgres, Supabase, Neon, D1, or Turso depending on how much relational/admin workflow is needed.
- Sync: cron or build job generates the search index every 15-60 minutes, uploads it, and updates a manifest/version hash.

The simpler fallback was:

- FlexSearch as the client-side index.
- Cloudflare D1 as source of truth.
- R2/static files for index delivery.
- Service Worker for index versioning.
- A secondary ingredient inverted index for fast include/exclude filtering.

## Package And Tool Inventory

### Search And Index Libraries

- Orama
- FlexSearch
- MiniSearch
- Fuse.js
- Lunr.js
- tantivy-wasm
- SQLite FTS5
- Meilisearch
- Typesense
- Algolia
- Elasticsearch

FlexSearch is likely the package remembered as "faster than Orama." The stored responses describe it as "faster, larger" and as a strong practical fallback. Orama was favored in the final synthesis because it is isomorphic, has faceting and geo support, and can be used in both browser Web Workers and edge workers.

### Browser / Local Database And Storage

- IndexedDB
- Dexie.js
- idb
- idb-keyval
- PGlite
- sql.js
- DuckDB-WASM
- Absurd-SQL
- OPFS
- RxDB

### Edge / Server / Database Options

- Cloudflare D1
- Turso / libSQL
- PostgreSQL / Postgres
- Supabase
- Neon
- PostGIS
- Cloudflare Workers
- Cloudflare R2
- Cloudflare KV / Workers KV
- Redis

### Frontend / App Frameworks

- Astro
- SvelteKit
- Svelte
- Next.js
- Remix
- Qwik City
- Vite
- React
- Preact
- Solid / SolidJS
- Hono

### Supporting Sync, Cache, And Data Format Tools

- Service Worker
- Workbox
- Web Worker
- MessagePack
- Protocol Buffers / Protobuf
- Orama binary `.oram`
- `@orama/plugin-data-persistence`
- Drizzle
- React Query / TanStack Query
- SWR

## Architecture Options Considered

### Pure Edge Database

Examples: Cloudflare D1, Turso/libSQL, SQLite FTS5.

Pros:

- Tiny initial payload.
- Fresh data on every query.
- Operationally simple at 50,000 rows.
- Good fit for admin/source-of-truth workflows.

Cons:

- Every keystroke has network latency, even if edge latency is low.
- SQLite FTS5 does not provide rich typo tolerance out of the box.
- Ingredient faceting can become awkward if modeled as SQL joins or JSON queries.

### Pure Browser Search

Examples: Orama, FlexSearch, MiniSearch, PGlite, sql.js, DuckDB-WASM, IndexedDB.

Pros:

- Fastest perceived UX after index load.
- Zero per-query server cost.
- Can work offline.
- Ingredient filters can be instant with facets or inverted indexes.

Cons:

- Initial index download can be costly on mobile.
- Needs cache invalidation and background update strategy.
- Freshness is harder for price changes, sold-out items, daily specials, and hours.

### Dedicated Search Engine

Examples: Meilisearch, Typesense, Algolia, Elasticsearch.

Pros:

- Best built-in typo tolerance, ranking, faceting, and filter UX.
- More proven for production search behavior.
- Easier than building all search semantics yourself.

Cons:

- Adds service and sync complexity.
- Likely heavier than necessary for a 50,000-item local MVP.
- Algolia was specifically called overkill/expensive for this scale.

### Hybrid Client Index + Edge Source Of Truth

Examples: Orama or FlexSearch in browser; D1/Turso/Postgres as source; R2/CDN for index delivery; edge endpoint for freshness checks.

Pros:

- Local search feels instant.
- Edge/source DB keeps data authoritative.
- Index can be cached across visits.
- Background patches can keep price/availability fresh.

Cons:

- More moving parts than pure edge DB.
- Patch/versioning logic needs care.
- Orama edge persistence and some implementation details may need validation before committing deeply.

## Practical Takeaway

For an MVP, the safest path is probably:

1. Build the first prototype with a small static dataset and a browser-side index.
2. Prefer FlexSearch if the immediate goal is a simple, fast, proven local search index.
3. Prefer Orama if geo filtering, facets, and shared browser/edge search code are important enough to justify newer tooling.
4. Keep D1, Turso, or Postgres as the eventual source of truth.
5. Avoid Meilisearch/Typesense until search quality, typo tolerance, or ranking needs exceed what the local index can comfortably handle.
