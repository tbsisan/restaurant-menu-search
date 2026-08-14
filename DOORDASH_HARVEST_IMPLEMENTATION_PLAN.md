# DoorDash menu-capture spike: implementation plan

## Purpose

Harden `spike_doordash_network_capture.py` so its harvest artifacts honestly
state what was captured, what failed, and whether menu completeness was
actually established.

Context and deliberation history are in:
`DOORDASH_HARVEST_COUNCIL_HANDOFF.md`.

## Implementation priorities

1. **Artifact honesty**

   Ensure an incomplete, failed, sampled, capped, or otherwise unproven run
   cannot be emitted as a complete menu capture. Persist enough result and
   failure evidence for a downstream consumer to understand the claim.

2. **Observable discovery**

   Make virtualized menu discovery report what it observed, how it stopped,
   and whether the page was usable. Preserve support for small menus that need
   no scrolling, without treating an unexplained zero-item result as success.

3. **Correct menu structure**

   Preserve category membership for items shown in both canonical and
   recommendation/cross-sell locations. Collection order must not silently
   decide the menu structure.

4. **Diagnosable item capture**

   Distinguish valid item-page payloads from transport, HTTP, GraphQL,
   malformed/changed-shape, wrong-item, and browser failures. Keep useful
   diagnostic evidence with the harvest.

5. **Safe recovery and resume**

   Confirm that a recovered tab and an existing checkpoint match the intended
   store/request before reusing them. Avoid contradictory duplicate item
   records after retries or resume. Preserve discovery progress when practical.

6. **State and selector hygiene**

   Keep diagnostic and collection selectors coherent. Repeated manual commands
   against the same live tab must not reuse stale page-side collection/network
   state.

## Validation before relying on the spike

Use permitted live pages or reproducible fixtures to exercise:

- a small no-scroll menu;
- a large virtualized menu;
- duplicate/cross-sell category appearances;
- delayed lazy loading or a collection stall;
- browser loss during discovery and item capture;
- non-success and changed-shape item-page responses;
- actual Camofox behavior for Promise evaluation, text-selector clicking, and
  the relevant scroll container.

Operational hypotheses must be tested before being promoted to code defects.

## Constraints

- Retain the direct `itemPage` capture path and its nested modifier data.
- Do not substitute incomplete JSON-LD for modifier capture.
- Do not add access-control, CAPTCHA, or bot-protection evasion.
- Keep changes proportionate to one spike; defer generic browser, retry,
  pacing, and multi-provider frameworks.
- Treat the harvest JSON as an interface contract with
  `parse_doordash_itempage.py`; coordinate schema changes with its consumer.

## Done when

One saved harvest file, without terminal logs, lets a reviewer determine:

- the source store/request;
- how discovery ended and whether it was sufficient;
- what items and category memberships were observed;
- which captures succeeded, failed, retried, or were intentionally limited;
- whether successful payloads were structurally usable;
- why `complete` is or is not true.
