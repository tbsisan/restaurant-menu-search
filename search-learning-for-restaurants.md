# Search Learning for Restaurant Menu Search

## Purpose

This note captures the reusable search work from the iNaturalist taxonomy
experiment and turns it into a concrete starting point for dish-level menu
search. It is deliberately more specific about text search, ranking, cache
boundaries, and UI behavior than about location narrowing; the location
implementation remains a separate responsibility.

The target working set is roughly 1,000 nearby restaurants with about 100 menu
items each: approximately 100,000 searchable menu items. That is small enough
for a relational database plus full-text search, but large enough that search
quality and interaction timing matter.

## What The Taxonomy System Actually Implements

The early D1 prefix-search proof of concept still exists in the repository, but
it is no longer an accurate description of the search system. The current
implementation is `../inatter-uploader/tools/do-taxonomy-worker/worker.js` plus
its browser client, index builders, maintenance scripts, and benchmark suite.

Keep these boundaries clear throughout this note:

- The taxonomy system below is implemented and was deployed through a sequence
  of measured changes.
- Restaurant adaptations remain recommendations until the menu corpus and
  judged query set validate them.
- Some maintenance improvements in `DECISIONS.md`, especially incremental index
  refresh, are designs rather than shipped code.

### Storage and indexes

Each of nine geographically placed Cloudflare Durable Object shards holds an
identical SQLite taxonomy database. The searchable structures are:

- a normalized `taxa` table with rank, scientific name, major-rank lineage,
  active state, and observation-count popularity;
- a one-to-many `common_names` table;
- a contentless FTS5 table over scientific name, common names, and lineage,
  with prefix indexes for lengths 3–6;
- a contentless trigram FTS5 table over scientific and common names; and
- an ordinary indexed `(phonetic_code, taxon_id)` table built from individual
  scientific-name and common-name words.

Derived indexes are built in resumable chunks. The phonetic code index is
created only after millions of rows are inserted, avoiding the cost of
maintaining its B-tree during the bulk load. Popularity is loaded at species
level and rolled up to higher taxa as a lower-bound descendant total.

This separation matters for menu search: normalized source records remain the
truth, while several purpose-built candidate indexes can be rebuilt from them.

### Public phases are server-owned

The public API accepts only the query, offset, and a named phase. Pool sizes and
ranking knobs are fixed server-side so a caller cannot turn an ordinary search
into an unbounded diagnostic query.

The current `fast` and `refine` phases run the **same complete search stack**:
prefix retrieval, conditional trigram retrieval, phonetic retrieval, merge, and
the same reranker. They differ primarily in the trigram candidate ceiling:

- `fast`: fuzzy pool 1,000;
- `refine`: fuzzy pool 10,000.

The prefix pool is 500 by default, the phonetic pool is capped at 3,000, public
pages default to 20 rows, and the endpoint caps a page at 50. These are measured
taxonomy values, not grocery or restaurant constants.

The larger refine pool exists for candidate membership, not finer scoring.
`Impatiens pallida` could be absent from a 1,000-row pool and rank first once the
10,000-row pool admitted it. A reranker cannot rescue a row retrieval discarded.

### Three candidate sources

#### Tier 1: exact and token-prefix FTS

Tier 1 provides the immediate high-confidence candidates. It searches names,
common names, and lineage through FTS5. Before its SQL `LIMIT`, direct
scientific-name prefixes are ordered ahead of rows that matched only through
lineage. This fixed a real pool-pollution failure: a query for a large genus
could fill the pool with short names elsewhere in the same family before the
genus's own species reached the reranker.

The transferable rule is stronger than “weight names highly”: a primary-field
match must receive priority while deciding **pool membership**, before the
limit, because a later weight cannot restore a discarded row.

#### Tier 2: ordered-window trigram FTS

The typo tier is not a generic bag-of-trigrams query. It slides a five-character
window across the normalized query, quotes each window as an FTS phrase, and ORs
those phrases together. Each phrase requires its overlapping trigrams to appear
consecutively and in order. A local typo destroys only nearby windows while
intact portions can still retrieve the intended name.

This design was chosen because bare trigram AND is brittle to one typo and bare
trigram OR admits fragments scattered anywhere and in any order. FTS `bm25`
orders the match set before the pool limit; it controls which rows survive into
the candidate set, while the application reranker controls final display order.

Tier 2 is expensive relative to Tier 1, so the worker gates it off when an
unsaturated prefix pool contains a zero-prefix-distance scientific-name match.
It refuses to gate when Tier 1 hit its limit, because a saturated pool proves
that some rows were discarded. It also does not gate on a common-name hit in the
current taxonomy implementation. The gate was tested for misfires, but its own
decision note correctly calls real-user typo data a remaining source of risk.

#### Tier 3: phonetic “super-fuzz”

The later taxonomy implementation added a third retrieval strategy for errors
that share no useful trigram with the intended name. Its `latinCodes()` encoder
collapses doubled letters, normalizes Latin/Greek spelling patterns, retains the
first character, removes later vowels, and may emit multiple codes for an
ambiguous soft `c`. The resulting lookup is an indexed equality query; the
fuzziness lives in the encoder.

Codes are indexed per word rather than per whole name. Multiword query hit sets
are intersected first and fall back to a union if the intersection is empty.
When a small hit set resolves to a genus or family, the worker can expand up to
three hierarchy matches to their species descendants. All candidates feed the
same string reranker; a phonetic code is never itself a final relevance score.

The phonetic tier is best-effort. A missing or rebuilding phonetic index records
degradation and falls back to prefix/trigram results instead of failing search.
It added only 2–13 ms to the measured fast phase, so it was folded into both
existing phases rather than adding a third browser repaint.

The Latin-specific encoder outperformed default Double Metaphone on the sampled
scientific-name corpus (96.9% versus 94.8% unique species codes) and handled
Greek-derived `ch` cases that Double Metaphone misread. Restaurant search should
start with default Double Metaphone and earn any food-specific override through
judged tests.

### The shared reranker

Candidates from all retrieval sources are deduplicated by stable taxon ID, then
each row's score components are computed once before sorting. The current
ranking uses several different notions of closeness because one distance cannot
serve exact lookup, typeahead, suffix fragments, aliases, and qualified queries
equally well:

- **substring distance (`sd`)** lets a query fragment match anywhere in a name;
- **prefix distance (`pd`)** prefers the beginning of a name and supports
  typeahead without penalizing the untyped tail;
- **full Levenshtein distance (`d`)** separates genuinely close spellings from
  loose prefix ties;
- **exact full-name match** beats popularity, whether the exact value is the
  scientific name or a common name;
- **popularity** enters at its specifically tested comparator position;
- **classic-rank preference** favors the familiar Linnaean rank when identical
  names occur at genus, subgenus, section, or another rank; and
- name length and taxon ID provide deterministic final tie breakers.

The exact deployed order is worth recording. For ordinary queries it is
substring distance → prefix distance → exact-complete-name flag → popularity →
full distance → classic rank → length → ID. For lineage-aware multiword queries
it is best lineage-or-phrase substring → prefix → full distance → exact flag →
popularity → classic rank → length → ID. Restaurant search need not copy
popularity ahead of full distance; the lesson is to make the comparator explicit
and validate each placement against domain examples.

The substring metric was added after prefix distance ranked a merely similar
front fragment above true `-icola` suffix matches. Prefix distance remains the
next key so a genuine beginning-of-name match still wins among equal substring
matches.

For multiword queries, a lineage-aware mode compares each query word against
the taxon's name words and major-rank lineage, then sums the best per-word
substring, prefix, and full distances. This makes a qualified query such as
`Fungi septoria` prefer the fungal genus rather than an unrelated trigram
lookalike. The extra work is gated to multiword queries.

### Aliases/common names are phrases, not a shared word bag

FTS retrieval already indexed common names, but the original reranker scored
only scientific names. That made a common-name hit such as `mallard` sink below
Latin-name lookalikes. The shipped fix scores the scientific name and each
complete common-name phrase, retains the best score, and returns the particular
common name that explains the match.

Common-name words are deliberately excluded from the lineage token bag. When
all aliases were flattened together, one query word could match one alias and a
second word another unrelated alias, creating a result no complete alias
supported. Restaurant aliases, alternate dish names, and source spellings need
the same phrase boundary and match-provenance rule.

### Input and client correctness

The browser waits for four non-space characters and debounces for 120 ms. It
collapses repeated whitespace and removes leading whitespace but preserves a
trailing space. In taxonomy typeahead, `Rosa ` means the genus token is complete
and an epithet is beginning; trimming it made that query indistinguishable from
`Rosa` and buried species under `Rosales`. Retrieval uses a trimmed copy where
FTS syntax requires it, while ranking keeps the boundary signal.

The client launches fast and refine concurrently. Refine is routed to a partner
shard because a Durable Object is single-threaded and would otherwise serialize
the requests. Fast may paint first, but refine replaces it; if refine arrives
first, a later fast response is forbidden from downgrading the page. Each search
increments a sequence number and aborts the prior controller so an obsolete
query cannot repaint newer results.

Pagination always uses refine and its current ordering. Paging into fast after
page one settled on refine would change the candidate universe and create skips
or duplicates. The interface labels partial counts with `+` instead of claiming
that the visible page equals the total match count.

### Routing, cold starts, and observability

The outer Worker chooses one of nine geographic shards from Cloudflare request
geography. Identical data permits two latency techniques:

- route refine to a nearby partner so fast and refine execute in parallel; and
- hedge a slow/cold primary against up to three kept-warm shards, taking the
  first healthy response.

Two shards are pinged every minute with `SELECT 1`. A true residency probe is
important: an earlier `/stats` probe scanned tables, polluted caches, consumed
CPU, and produced misleading “network” measurements. Cold shards are hedged
immediately; warm primaries receive a 150 ms grace period.

Search logging happens asynchronously after the response and records query,
phase, intended shard, answering shard, edge colo, latency, pool size, result
count, pagination state, status, and whether a hedge won. It intentionally
stores no IP or visitor identifier. Debug search can expose comparator inputs in
their exact order, which proved essential for separating retrieval misses from
ranking errors.

### Measurement discipline

The benchmark suite uses fixed species samples, paired configurations per query,
sequential requests to respect the Durable Object's single-threaded execution,
and separate exact, prefix, substitution, insertion, and deletion cases. Timing
is external because Workers freeze the in-process clock during synchronous
SQLite work. A `/ping` `SELECT 1` measures the network/dispatch floor.

An early benchmark was about 95% typos and had no prefix traffic, so its median
described the worst path. The replacement mix was 60% exact/prefix and 40%
typos. This correction is as reusable as any algorithm: evaluation traffic must
resemble actual typing, and exact/prefix and typo cohorts should be reported
separately.

The evidence is layered rather than one final benchmark of every shipped knob.
The broad quality summary predates the phonetic and substring defaults; those
features have their own targeted verification and regression runs in commits
and `bench/regress_pop_lin.py`. Before treating the current phase as a baseline
for another domain, rerun an integrated public-phase benchmark with all current
defaults enabled.

### Current implementation caveats not to copy

The end-to-end audit also exposed prototype edges that the transfer design
should harden:

- `taxa.active` is stored, but the current candidate queries do not explicitly
  filter `active = 1`; a new domain must enforce eligibility in every source.
- the lightweight `/reset` route drops taxa/common/FTS tables but not the
  phonetic table; a true rebuild must clear or version every derived index;
- the phonetic tier takes the first 3,000 IDs from an unordered hit set before
  reranking; mostly unique scientific-name codes keep this uncommon, but a food
  implementation needs deterministic or relevance-aware admission for large
  phonetic buckets;
- the public UI requires four characters, but the endpoint does not impose a
  hard maximum query length/token budget;
- Tier 1 catches malformed FTS prefix syntax and degrades, but new endpoints
  should compile and bound input deliberately rather than rely on exceptions;
  and
- the taxonomy UI inserts corpus fields with `innerHTML`; scraped restaurant
  strings require safe DOM construction or explicit escaping.

These are findings about the current prototype, not recommendations.

### Taxon-image decision

The image decision remains simple and transferable:

- return text results immediately;
- cache one representative image separately; and
- fetch additional examples only when a result expands.

Menu photos must never delay the first search result. Image loading is an
enrichment path, not a retrieval dependency.

## Transferable Principles

1. Search a prepared representation, not raw scraped text.
2. Do the deterministic, high-confidence pass first.
3. Run typo tolerance only on a bounded candidate set.
4. Treat query cancellation and response ordering as correctness concerns.
5. Make ranking explainable enough to debug with real examples.
6. Keep search documents denormalized for retrieval, while retaining
   normalized source data for provenance and maintenance.
7. Filter the corpus before ranking whenever a stable filter, such as location
   or availability, is available.
8. Preserve source freshness, menu provenance, and the exact item identity;
   search should never hide uncertainty in the underlying menu data.

## Recommended Menu Search Shape

Use the taxonomy system's three-source candidate architecture and shared
reranker, exposed through two concurrent pool-size phases. Both phases must use
the same normalized query, location scope, filters, index version, retrieval
sources, and comparator. That consistency is what makes one phase safe to
replace with the other.

### Candidate sources inside each phase

1. **Name/alias prefix retrieval:** normalized dish names first, with approved
   aliases and restaurant-provided spellings. Category, cuisine, and description
   context may add candidates but must not crowd direct name matches out before
   the limit.
2. **Ordered-window trigram retrieval:** use overlapping quoted windows rather
   than an unordered bag, so a typo can break nearby fragments without making
   unrelated scattered fragments equivalent.
3. **Double Metaphone retrieval:** precompute codes per word for dish names,
   restaurant names, cuisines, and curated aliases. Start with the default
   English-oriented algorithm; add aliases or narrow overrides only after a
   judged food-name benchmark demonstrates a recurring miss.

Do not fuzzy-scan or phonetic-index entire descriptions or ingredient lists.
Those high-cardinality text fields create noisy candidate buckets. Phonetic
matching must never enforce ingredient or allergen exclusions.

### Fast and refine phases

The fast phase uses smaller bounded pools and paints as soon as it returns. The
refine phase runs concurrently with larger pools and replaces fast using the
same ranking policy. Tune the sizes against the menu corpus rather than copying
the taxonomy values of 1,000 and 10,000 blindly.

A query for `chicken shawarma` should surface literal name matches immediately;
`shwarma` should be recovered by ordered trigrams; and a sound-based spelling
with no useful shared n-gram should still have a path through Double Metaphone.
All three kinds of candidates must meet in one reranker so an approximate hit
cannot outrank an exact phrase simply because it came from another endpoint.

The taxonomy gate suggests an optimization after correctness is established:
skip the trigram tier when an unsaturated primary-name pool already contains a
zero-prefix-distance match. For menu search the gate must inspect every primary
identity field that can legitimately satisfy the query, and it must remain off
when the prefix pool saturated. Measure real-user misfires before treating it as
safe.

### Phase and pagination correctness

- Debounce lightly; 120 ms is the measured taxonomy setting and a reasonable
  starting point, not a universal constant.
- Attach one query sequence and complete filter signature to both phases.
- Abort old work and reject responses whose sequence is no longer current.
- If refine arrives first, never let late fast results downgrade the page.
- Keep pagination on refine after page one settles there; changing pool sizes
  between pages changes offsets and causes duplicates or omissions.
- Preserve a trailing token boundary separately from the FTS-safe trimmed query
  instead of applying unconditional `.trim()` at the input boundary.
- Return development-only candidate counts, retrieval reasons, comparator
  inputs, and the alias or field that explains each match.

## Why This Fits The Menu Corpus

At about 100,000 items, a full-text index can answer the first pass quickly.
Running general fuzzy comparison against every name and description on each
keystroke is unnecessary work and will produce noisy matches. A candidate-first
strategy gives most of the perceived speed of a small in-memory index while
keeping the source database authoritative.

The location filter should narrow restaurants before or during candidate
retrieval. The later location implementation may use a radius query, spatial
cells, a restaurant-ID set, or another mechanism, but the text ranker should
receive only items eligible for the current area.

## Search Document Design

Keep source tables normalized, then build one denormalized search document per
currently searchable menu item.

| Field | Purpose |
| --- | --- |
| menu_item_id | Stable item identity |
| restaurant_id | Join and location scope |
| canonical_name | Main ranked dish name |
| display_name | Restaurant-facing label |
| normalized_name | Case, punctuation, and diacritic-normalized name |
| aliases | Canonical synonyms, common spellings, source names |
| description | Scraped or cleaned item description |
| ingredient_terms | Searchable normalized ingredients |
| category_terms | Menu section and useful taxonomy such as appetizer |
| cuisine_terms | Optional cuisine signals |
| price_cents | Display and filters, not primary text rank |
| availability | Current known availability state |
| source_confidence | Quality of the extraction/source |
| last_verified_at | Freshness signal |
| popularity_signal | Optional tie breaker when trustworthy |

Do not collapse every restaurant's similar dish into one record at ingest time.
Search needs the restaurant-specific item, price, description, and provenance.
Canonical-dish grouping can be added as a secondary relationship later.

## Normalization And Aliases

Normalization should be conservative and reversible:

- Lowercase for lookup while preserving display text.
- Normalize whitespace, apostrophes, hyphens, punctuation, and diacritics.
- Preserve meaningful food terms; do not use a generic stop-word list that
  removes ingredients such as with, in, or style indiscriminately.
- Index singular/plural variants where useful.
- Keep the raw source name and every source spelling.
- Maintain aliases separately from automatic normalization.

Alias examples:

- shawarma, shawerma, and a restaurant-specific spelling.
- veg taco, veggie taco, and vegetarian taco when the menu evidence supports
  that equivalence.
- A proprietary dish name such as Dan's Ultimate linked to its descriptive
  ingredients, without replacing the original name.
- Swiss expanded to Swiss cheese as an ingredient term, but not silently
  turned into a different display name.

Aliases improve recall; they must not claim that two dishes are the same when
the menu does not support that conclusion.

## Ranking Policy

Start with transparent, inspectable scoring. Carry over the taxonomy ranker's
separation between substring, prefix, and full edit distance rather than
collapsing them into one “fuzzy score.” A sensible initial priority order is:

1. Exact normalized full-name match.
2. Exact phrase in dish name.
3. Exact complete approved-alias match.
4. All query tokens in dish name, in order or close together.
5. Prefix match in dish name or approved alias.
6. True substring/fragment match when the query shape calls for it.
7. Trigram or phonetic candidate reranked by original-string edit distance.
8. Strong ingredient and description match.
9. Category or cuisine-context match.

Score each alias as a complete phrase and return the alias or field that caused
the match. Never let different query words match pieces of unrelated aliases.
Precompute score components once per candidate, then use stable final keys so
ties do not reshuffle between requests.

Only after text relevance is established should the system use tie breakers:

- restaurant distance or location relevance;
- source freshness and confidence;
- availability;
- price, only when the user expresses a price preference;
- popularity, only if the signal is defensible.

Do not let a nearby restaurant with a weak text match outrank an exact dish
match by default. The product is craving-first.

## Ingredient Search Is Not The Same As Dish-Name Search

The interface may expose one input, but internally distinguish intent:

- A query like birria tacos is primarily a dish-name search.
- A query like contains mushrooms or no peanuts is ingredient logic.
- A query like vegetarian pad thai mixes a dish name with a constraint.

For the first version, use documented search fields and ranking rather than
pretending to fully understand arbitrary natural-language constraints. Add
explicit include/exclude ingredient filters once ingredient extraction quality
supports them.

Ingredient exclusions are hard eligibility filters, not negative relevance
weights and not phonetic matches. Track at least three states: explicitly
present, not found in a sufficiently complete parsed ingredient source, and
unknown because the source is absent or incomplete. A preference filter may
retain unknowns with a warning or offer a strict “remove unknowns” option.
Neither mode proves allergy safety: absence from a scraped menu description is
not proof that a dish is free of an ingredient or cross-contact risk.

## API And Concurrency Model

The simplest reliable two-phase contract launches two independent requests in
parallel, both backed by the same retrieval and ranking code:

1. GET /api/search/fast?q=...&location=...&filters=...
2. GET /api/search/refine?q=...&location=...&filters=...

Each request/response must include:

- query_id: monotonically increasing value created by the browser;
- normalized query and active filter signature;
- index/data version;
- result phase: fast or refine;
- candidate counts by retrieval source and whether any expensive tier was
  gated off, in development;
- timing metadata in development;
- per-result match reasons or score bands in development.

Client behavior:

- Abort both in-flight requests when the query or filters change.
- Start both requests after the same debounce.
- Render fast as soon as it resolves.
- Ignore refine if its query ID or filter signature is no longer current.
- Never allow fast to repaint after refine has already settled.
- Replace or minimally update the result list only when refine adds relevant
  items or changes meaningful order.
- Keep scroll position and keyboard focus stable across the repaint.
- Page only against refine after refine establishes page-one ordering.

One streaming endpoint is possible later, but two ordinary requests are easier
to cache, test, observe, and cancel.

## Database Retrieval Pattern

The exact database choice is open. The core pattern is not:

1. Resolve the eligible restaurant subset from location and other stable
   filters.
2. Retrieve a bounded direct/prefix pool, preserving primary-field matches
   before its limit.
3. Retrieve bounded ordered-window trigram and phonetic pools when applicable.
4. Merge and deduplicate candidates by stable menu-item identity.
5. Apply hard availability and ingredient filters before the visible limit.
6. Fetch display/provenance fields and compute the shared transparent rerank.

SQLite FTS5 is viable for both token-prefix and trigram candidate indexes. A
normal tokenizer is not typo tolerant; the separate FTS5 trigram table and
phonetic table provide approximate recall. The current taxonomy worker uses a
custom JavaScript distance reranker; RapidFuzz was an earlier plan, not the
deployed implementation.

Do not assume a standard FTS5 table provides arbitrary substring search. Use
prefix matching for the first pass, and add an appropriate tokenizer, n-gram
index, or the typo-recall lexicon above if infix matching is a real product
requirement.

Compile user input into a constrained FTS query instead of appending raw input
to MATCH syntax. Bound query length, normalize/tokenize terms, escape or reject
FTS operators and punctuation, and define the AND/OR behavior deliberately.
Parameter binding prevents SQL injection, but malformed FTS syntax can still
make a search endpoint error or behave unexpectedly.

For a browser-index or hybrid implementation, the existing stack research
records the tradeoff between a CDN-cached browser index and edge/database
search. Do not ship the entire 100,000-item corpus to every first-time visitor
until a measured performance need justifies it. A location-scoped edge query
is the simpler first production path.

## Technologies Considered

The earlier menu-search research considered several workable families. At this
scale, none is categorically required; the right choice is the one that keeps
ingestion, relevance tuning, and location scoping understandable.

| Option | Good at | Tradeoff | Current posture |
| --- | --- | --- | --- |
| Cloudflare D1 plus Workers | Small operational footprint, edge API, SQLite/FTS-style retrieval, static-site deployment in the same platform | Free-plan CPU is tight; typo tolerance and advanced geospatial behavior need deliberate design | Recommended first production path |
| Turso/libSQL | Edge-distributed SQLite and straightforward SQLite ergonomics | Another vendor/service beside hosting; less benefit from the existing D1 work | Strong alternative if SQLite developer experience or replication becomes the deciding factor |
| Postgres, including Neon or Supabase | Rich joins, PostGIS, pg_trgm, mature admin/query tools | More operations and another deployment boundary for a small local MVP | Best escalation path if location and relational operations become the hard part |
| Browser index, such as FlexSearch, Orama, or MiniSearch | Instant repeated searches and offline-capable interaction | First-load payload, index versioning, and stale-menu complexity | Consider later as a cache or hybrid layer, not the initial default |
| Fuse.js-style in-memory fuzzy search | Simple prototype fuzzy matching | Poor primary retrieval strategy as the corpus grows; must be scoped to candidates | Useful only for a small candidate set or fixture/demo |
| Meilisearch or Typesense | Built-in typo tolerance, facets, filters, and fast relevance tuning | Another service and sync pipeline | Revisit if FTS plus bounded fuzzy rerank is measurably inadequate |
| Algolia | Polished hosted search and analytics | Cost and vendor dependence are disproportionate for this local corpus | Not a first-MVP choice |
| Elasticsearch/OpenSearch | Powerful full-scale search | Operationally heavy and unnecessary here | Explicitly avoid until scale or requirements change radically |
| PGlite, sql.js, DuckDB-WASM, or a browser database | Interesting local/offline experiments | Larger client complexity and no clear first-pilot advantage | Research tools, not the default application architecture |

## Why Start With Cloudflare

Cloudflare is the practical default because the current taxonomy system already
runs as a Worker fronting SQLite-backed Durable Object replicas; D1 is used for
asynchronous search/visit logs. A menu-search first release can keep the public
API, static frontend, database binding, cache, and optional static index asset
in one deployment model. That reduces handoffs and avoids choosing a dedicated
search service before evidence says it is needed.

Do not copy the nine-identical-shard topology automatically. It was a response
to a global, read-mostly taxonomy corpus and Durable Object cold starts. A local
restaurant corpus may be better served by fewer replicas or a location-partitioned
database. If two phases target one single-threaded object, either route refine
to an identical partner or accept that the requests will serialize.

For the current target, query discipline and write amplification are the main
Cloudflare concerns. Location scope and FTS indexes must prevent broad scans,
and fuzzy work must remain bounded. Measure rows read and rows written during
ingestion and real searches rather than guessing; count every derived index and
every replica, not just source-table mutations.

### Cloudflare limits and the row-write incident

Verified against Cloudflare documentation on 2026-08-20; recheck before
committing a production architecture. The taxonomy search corpus is stored in
SQLite-backed Durable Objects. D1 is a separate database used for asynchronous
search/visit logs, so D1 was not the source of this incident.

- Workers Free allows 100,000 requests per day, 10 ms CPU time per HTTP
  request, 50 subrequests per invocation, and 128 MB per isolate. The CPU
  allowance reinforces the need for prebuilt, bounded retrieval instead of a
  corpus-wide fuzzy scan.
- SQLite-backed Durable Objects on Free allow 5 million rows read per day,
  100,000 rows written per day, and 5 GB total stored data. Durable Object
  requests also share the 100,000-per-day Free allowance. Exceeding a daily
  storage-operation allowance can make an import fail rather than merely make
  it expensive.
- On Paid, the first 25 billion SQLite rows read and 50 million rows written per
  month are included. Additional reads cost $0.001 per million; additional
  writes cost $1 per million. Inserts, updates, deletes, and affected index
  entries all contribute row operations. Deleting and recreating an index is
  therefore not free cleanup.
- D1 currently uses the same 5-million-read and 100,000-write daily Free
  allowances, and the same Paid row rates. Those limits matter for logs, but
  they must not be confused with the Durable Object corpus metrics.

The failure mode that bit the taxonomy system was write amplification during a
full refresh. A modest monthly source delta was turned into writes for the base
taxa, FTS, ordered trigrams, roughly 3.6 million phonetic rows per replica,
common names, popularity data, rollups, and SQLite indexes, then copied to all
nine identical Durable Objects. The current drop-and-recreate path is estimated
at roughly 180–230 million row writes per monthly rebuild. On Paid, subtracting
the 50-million included allowance leaves about 130–180 million billable writes,
or approximately $130–180 each month, before other usage.

This is an architecture constraint, not a minor billing footnote. Restaurant
menus change far more often than biological taxonomy, so do not rebuild every
text, trigram, and phonetic index on every price, availability, or menu-state
change. Separate relatively stable searchable dish content from volatile offer
state; patch only changed documents and derived keys; use tombstones or an
atomic version switch where necessary; and multiply measured writes by the
actual replica count before choosing a topology. A full rebuild should be an
explicit recovery/migration operation with a measured write budget.

Cloudflare references:

- [Workers limits](https://developers.cloudflare.com/workers/platform/limits/)
- [Durable Objects pricing](https://developers.cloudflare.com/durable-objects/platform/pricing/)
- [D1 pricing](https://developers.cloudflare.com/d1/platform/pricing/)
- [D1 limits](https://developers.cloudflare.com/d1/platform/limits/)

## Index Maintenance

Search quality depends on index hygiene more than sophisticated matching.

- Rebuild or update the search document whenever a menu source changes.
- Write source rows and search index updates transactionally where possible.
- Mark removed items as inactive rather than deleting provenance.
- Version every index build.
- Invalidate query cache entries when the relevant index version changes.
- Keep source-specific price and availability timestamps.
- Record parsing confidence and source URL alongside searchable items.

The taxonomy FTS tables are contentless. That made the large static index
compact, but contentless FTS historically complicated delete/update operations.
The current full refresh rebuilds all derived indexes; an incremental-refresh
design using delete-capable contentless FTS or tombstones is documented but not
implemented. Restaurant menus change much more often than taxonomy, so settle
the mutation strategy before adopting that schema:

- use an updateable/external-content FTS design;
- use verified `contentless_delete` support;
- filter versioned tombstones before reranking; or
- build a fresh version and switch atomically.

Whichever strategy is chosen, refresh name, alias, trigram, phonetic, and
derived ranking signals as one versioned chain. A partial refresh can silently
leave one retrieval tier stale.

The taxonomy project also exposed a source-cadence mismatch: monthly taxonomy
IDs and more frequently pulled popularity counts can disagree after taxon swaps,
leaving a real item with a misleading zero or a count for an ID absent from the
snapshot. Its proposed mitigation is to pull related data close together and
anti-join important missing IDs for reconciliation. Restaurant menus have the
same class of problem across menu text, prices, availability, ratings, and
source-specific IDs. Record each source version/time, never translate a failed
join into a confident zero, and reconcile identity drift before rebuilding
derived ranking signals.

For a small local corpus, a full index rebuild after an ingestion batch may be
simpler and safer than delicate partial-index logic. Move to incremental updates
only when rebuild time or freshness requirements make it necessary.

## Caching

Cache at three layers, each with a different purpose:

- Browser: retain the current query results long enough to avoid repeated
  requests while the user edits a query.
- Edge/API: cache normalized fast-query responses by query, location scope,
  filters, and index version.
- Database/index: rely on the full-text index for retrieval, not a cache of
  raw scraped menus.

Do not cache availability, specials, or prices so long that the cache becomes
more trustworthy-looking than the source data. Freshness belongs in the result
record and may need to influence UI presentation.

## Result Presentation Requirements

Every result should make the choice legible without a restaurant-detail visit:

- dish name;
- restaurant name;
- concise description or key ingredients;
- price when available;
- location/distance supplied by the location layer;
- source freshness/confidence when it affects trust;
- clear match highlighting for the dish name or ingredients.

Avoid duplicate-looking results from the same item across multiple sources.
Choose a canonical current source for display, while retaining the competing
source records behind the scenes.

Render scraped names, descriptions, and aliases with text-safe DOM APIs or
explicit escaping. The taxonomy prototype uses `innerHTML` for trusted corpus
fields; restaurant content is external input and should not inherit that XSS
surface.

Images, ratings, and review summaries should load after text results. They are
valuable comparison information, not prerequisites for answering a food query.

## Evaluation Set

Build a small hand-judged relevance set before optimizing. Each case should
identify the expected top results and why.

Include:

- exact dish: chicken shawarma;
- punctuation/spacing: mac n cheese;
- a multiword prefix with a meaningful trailing token boundary;
- typo: shwarma;
- a typo that ordinary trigrams recover;
- a severe or sound-based misspelling with no useful shared trigram;
- a phonetic collision that final string reranking must demote;
- alias: veggie tacos;
- multiple aliases where query words must not scatter across different phrases;
- an exact alias that must beat a more popular prefix match;
- a mid-word or suffix fragment that tests substring versus prefix distance;
- proprietary name plus description: Dan's Ultimate;
- ingredient-led query: mushroom;
- an ingredient exclusion with present, absent, and unknown-source items;
- multiword dish: corned beef egg rolls;
- generic word with many matches: chicken;
- no result;
- stale or unavailable item;
- a query where a nearby weak match must not outrank an exact farther match.

Track:

- first-pass server latency;
- time to first visible results;
- refine completion time;
- candidate count and saturation by retrieval source;
- trigram-gate fire and misfire rate;
- incremental recall attributable only to phonetic retrieval;
- top-1 and top-5 judged relevance;
- percentage of fuzzy repaints that materially improve results;
- zero-result rate and successful reformulation rate;
- stale-result incidents.

Initial targets for a local pilot:

- Fast pass usually feels immediate after debounce.
- Refine completes before the user has to pause and reconsider the query.
- No stale response can replace a newer query's results.
- Exact and well-known local dish spellings are reliably top-ranked.

## Delivery Sequence

1. Create a representative local fixture with real menu-name, description,
   alias, and provenance edge cases.
2. Build the fast location-scoped FTS search and an inspectable ranking trace.
3. Add ordered-window trigram retrieval and the shared distance reranker.
4. Add default Double Metaphone retrieval and measure its incremental recall.
5. Add fast/refine pools, query sequence IDs, abort handling, and stable repaint.
6. Add ingredient filters with explicit unknown handling.
7. Add freshness/confidence to result display and an atomic index-refresh path.
8. Measure against the 100,000-item target shape with a realistic query mix.
9. Consider a browser-cached index only if observed edge latency or query cost
   makes the simple architecture insufficient.

## Things To Avoid

- Fuzzy-scanning all menu items on every keystroke.
- Reusing the taxonomy's Latin/Greek phonetic encoder, or customizing default
  Double Metaphone before a judged food-name benchmark shows why.
- Using phonetic similarity to enforce ingredient exclusions.
- Searching raw scraped blobs without normalized fields and aliases.
- Sending the entire citywide corpus to every browser by default.
- Ranking popularity, distance, or price above a clearly better dish-name
  match.
- Treating missing ingredient text as a dietary guarantee.
- Allowing an old fast/refine response to overwrite a newer query or filter set.
- Paging against a different pool or ordering than the settled first page.
- Trimming away meaningful token-boundary state before ranking sees it.
- Rebuilding only one derived retrieval index after source data changes.
- Hiding stale data or source disagreement behind a single confident result.
- Building a dedicated search service before a measured limitation of FTS plus
  candidate reranking appears.

## Source Notes

This note synthesizes:

- ../inatter-uploader/PLAN-uploader.md (planned local taxonomy FTS and fuzzy
  architecture);
- ../inatter-uploader/tools/do-taxonomy-worker/DECISIONS.md, worker.js,
  public/index.html, index builders, and bench/ (the current implementation,
  client behavior, maintenance path, and measurement evidence);
- ../inatter-uploader/tools/d1-taxonomy-worker/worker.js (implemented
  prefix-FTS D1 proof of concept);
- external-data/derived/search-stack-research-2026-06-22.md (menu-search
  architecture research).

It intentionally does not settle location narrowing, geography permissions, or
the final database/vendor choice.
