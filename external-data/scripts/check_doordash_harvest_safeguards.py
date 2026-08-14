"""Review harness: exercise the safeguards the validation checklist claims exist.

STATUS: this is the throwaway harness written during the 2026-08-14 code review,
preserved verbatim so it is not lost. It is NOT the regression suite. Two checks
fail BY DESIGN -- they demonstrate confirmed defects (retryable-but-never-retried,
and unhandled browser loss during discovery). See
external-data/menu-scraping/doordash-harvest-next-steps.md Step 2, which converts
this into a real pytest suite and covers the parser->normalizer stage it omits.

Run: .venv/bin/python external-data/scripts/check_doordash_harvest_safeguards.py
Expected today: 28/30 passing.
"""
import importlib.util, json, sys, tempfile, types, traceback
from pathlib import Path

ROOT = Path("/home/tbsisan/Projects/restaurant-menu-search")
spec = importlib.util.spec_from_file_location(
    "spike", ROOT / "external-data/scripts/spike_doordash_network_capture.py")
spike = importlib.util.module_from_spec(spec)
spec.loader.exec_module(spike)

import requests

results = []
def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + ((" :: " + detail) if detail else ""))


# ---------- fetch_item_page branches ----------
class FakeClient:
    def __init__(self, response): self.response = response
    def evaluate(self, tab_id, expr, timeout=60):
        if isinstance(self.response, Exception): raise self.response
        return self.response

def diag(response, item_id="42"):
    return spike.fetch_item_page(FakeClient(response), "t", "99", item_id, "query")

good_page = {"itemHeader": {"id": "42", "name": "Taco"}, "optionLists": []}
cases = {
    "success":                ({"status": 200, "body": json.dumps({"data": {"itemPage": good_page}})}, True, "success"),
    "http_error":             ({"status": 503, "body": "upstream"}, False, "http_error"),
    "graphql_errors":         ({"status": 200, "body": json.dumps({"errors": [{"message": "boom"}]})}, False, "graphql_errors"),
    "response_not_json":      ({"status": 200, "body": "<html>nope"}, False, "response_not_json"),
    "missing_item_page":      ({"status": 200, "body": json.dumps({"data": {}})}, False, "missing_item_page"),
    "malformed_item_page":    ({"status": 200, "body": json.dumps({"data": {"itemPage": {}}})}, False, "malformed_item_page"),
    "item_identity_mismatch": ({"status": 200, "body": json.dumps({"data": {"itemPage": {"itemHeader": {"id": "999"}}}})}, False, "item_identity_mismatch"),
    "network_fetch_error":    ({"fetch_error": "TypeError: failed"}, False, "network_fetch_error"),
    "malformed_wrapper":      ({"status": "200", "body": "{}"}, False, "malformed_response_wrapper"),
    "camofox_evaluate_error": (requests.HTTPError("404 tab gone"), False, "camofox_evaluate_error"),
    "camofox_bad_result":     ("not-a-dict", False, "camofox_evaluate_invalid_result"),
}
for label, (resp, want_ok, want_kind) in cases.items():
    out = diag(resp)
    got_kind = out["diagnostic"].get("kind") or out["diagnostic"].get("outcome")
    check(f"fetch_item_page/{label}", out["ok"] == want_ok and got_kind == want_kind,
          f"ok={out['ok']} kind={got_kind}")

# retryable flags actually honoured by the caller's retry set?
retry_set = {"camofox_evaluate_error", "camofox_evaluate_invalid_result"}
claims_retryable = {label for label, (resp, _, kind) in cases.items()
                    if diag(resp)["diagnostic"].get("retryable")}
kinds_retryable = {cases[l][2] for l in claims_retryable}
check("retryable diagnostics are all actually retried by cmd_harvest",
      kinds_retryable <= retry_set, f"claim retryable but never retried: {sorted(kinds_retryable - retry_set)}")


# ---------- build_harvest_status ----------
disc_complete = {"status": "complete", "stop_reason": "bottom_stable"}
sel_live = {"source": "live_discovery", "sample_per_section": None, "sample_seed": None, "item_limit": None}
items = [{"item_id": "1"}, {"item_id": "2"}]
ok_results = [{"item_id": "1", "item_page": {}}, {"item_id": "2", "item_page": {}}]

h = spike.build_harvest_status(selected_items=items, results=ok_results,
                               discovery=disc_complete, selection=sel_live, finished=True)
check("clean run -> complete", h["state"] == "complete" and not h["reasons"], str(h["reasons"]))

h = spike.build_harvest_status(selected_items=items, results=ok_results[:1],
                               discovery=disc_complete, selection=sel_live, finished=True)
check("missing capture -> incomplete/pending",
      h["state"] == "incomplete" and "item_page_captures_pending" in h["reasons"], str(h["reasons"]))

h = spike.build_harvest_status(selected_items=items, results=ok_results,
                               discovery={"status": "incomplete", "stop_reason": "scroll_limit_reached"},
                               selection=sel_live, finished=True)
check("capped discovery -> incomplete", h["state"] == "incomplete", str(h["reasons"]))

h = spike.build_harvest_status(selected_items=items, results=ok_results,
                               discovery=disc_complete,
                               selection={**sel_live, "item_limit": 5}, finished=True)
check("--limit -> incomplete", h["state"] == "incomplete" and "item_selection_limited" in h["reasons"], str(h["reasons"]))

h = spike.build_harvest_status(selected_items=items, results=ok_results,
                               discovery=disc_complete,
                               selection={**sel_live, "source": "items_file"}, finished=True)
check("--items-file can never be complete", h["state"] == "incomplete", str(h["reasons"]))

h = spike.build_harvest_status(selected_items=[], results=[], discovery=disc_complete,
                               selection=sel_live, finished=True)
check("empty selection -> incomplete", h["state"] == "incomplete", str(h["reasons"]))


# ---------- collect_items with a scripted page ----------
class ScriptedClient:
    """Answers evaluate() by inspecting which JS blob was sent."""
    def __init__(self, *, cards, problem=None, grows=False, die_after=None, at_bottom=True):
        self.cards, self.problem, self.grows = cards, problem, grows
        self.die_after, self.at_bottom = die_after, at_bottom
        self.calls = 0
        self.n = cards
    def evaluate(self, tab_id, expr, timeout=60):
        self.calls += 1
        if self.die_after is not None and self.calls > self.die_after:
            raise requests.HTTPError("404 Not Found: tab gone")
        if expr == spike.DISMISS_PROBE_JS: return {"visible": False}
        if expr == spike.DISCOVERY_PAGE_STATE_JS:
            return {"ready_state": "complete", "rendered_menu_card_count": self.n,
                    "visible_menu_card_count": self.n, "category_headings": ["Tacos"],
                    "problem_signals": [self.problem] if self.problem else []}
        if expr == spike.RESET_COLLECTION_JS: return {"url": "https://x/store/a-1", "reset": True}
        if expr == spike.COLLECT_STEP_JS:
            if self.grows: self.n += 3
            return {"total": self.n, "eligible_cards_in_view": self.n, "selector_counts": {}}
        if expr.startswith("(function(){\n  window.scrollBy"):
            return {"y": 0, "h": 800, "viewport": 800, "at_bottom": self.at_bottom}
        if expr == spike.COLLECTED_JS:
            return [{"item_id": str(i), "section": "Tacos", "sections": ["Tacos"]} for i in range(self.n)]
        return None

items_out, disc = spike.collect_items(ScriptedClient(cards=5), "t", max_scrolls=60)
check("small no-scroll menu -> bottom_stable/complete",
      disc["stop_reason"] == "bottom_stable" and disc["status"] == "complete" and items_out,
      f"{disc['status']}/{disc['stop_reason']} items={len(items_out)}")

items_out, disc = spike.collect_items(ScriptedClient(cards=0, problem="verify you are human"), "t")
check("bot-check page -> not complete",
      disc["status"] == "incomplete" and disc["page_usable"] == "no", f"{disc['status']}/{disc['stop_reason']}")

items_out, disc = spike.collect_items(ScriptedClient(cards=3, grows=True, at_bottom=False), "t", max_scrolls=6)
check("still-growing menu at cap -> incomplete",
      disc["status"] == "incomplete" and disc["stop_reason"] == "scroll_limit_reached",
      f"{disc['status']}/{disc['stop_reason']}")

# browser loss mid-discovery
try:
    spike.collect_items(ScriptedClient(cards=4, grows=True, die_after=6), "t", max_scrolls=60)
    check("browser loss during discovery is handled", False, "no exception, no error path taken")
except requests.RequestException as exc:
    check("browser loss during discovery is handled", False,
          f"uncaught {type(exc).__name__} escapes collect_items -> traceback, no discovery record")
except Exception as exc:
    check("browser loss during discovery is handled", False, f"uncaught {type(exc).__name__}")


# ---------- resume / checkpoint safety ----------
tmp = Path(tempfile.mkdtemp(prefix="dd-harvest-check-"))
cp = tmp / "harvest.json"
sel_items = [{"item_id": "1", "section": "Tacos", "sections": ["Tacos"]},
             {"item_id": "2", "section": "Tacos", "sections": ["Tacos", "Most Ordered"]}]
spike.write_harvest(cp, "https://x/store/a-1", "1",
                    [{"item_id": "1", "item_page": {"itemHeader": {}}, "menu_position": 0}],
                    selected_items=sel_items, discovery=disc_complete, selection=sel_live, finished=False)
prev, reason = spike.load_previous(cp, store_url="https://x/store/a-1", store_id="1",
                                   selection=sel_live, selected_items=sel_items)
check("resume reuses validated successes", set(prev) == {"1"} and reason is None, f"{sorted(prev)} {reason}")

prev, reason = spike.load_previous(cp, store_url="https://x/store/a-1", store_id="2",
                                   selection=sel_live, selected_items=sel_items)
check("resume refuses store-id mismatch", not prev and reason == "checkpoint_store_id_mismatch", str(reason))

prev, reason = spike.load_previous(cp, store_url="https://x/store/a-1", store_id="1",
                                   selection={**sel_live, "item_limit": 3}, selected_items=sel_items)
check("resume refuses selection mismatch", not prev and reason == "checkpoint_selection_mismatch", str(reason))

legacy = tmp / "legacy.json"
legacy.write_text(json.dumps({"source_url": "https://x/store/a-1", "store_id": "1", "complete": True,
                              "items": [{"item_id": "1", "item_page": {}}]}))
prev, reason = spike.load_previous(legacy, store_url="https://x/store/a-1", store_id="1",
                                   selection=sel_live, selected_items=sel_items)
check("pre-contract artifact not resumed", not prev and reason == "checkpoint_has_no_compatible_harvest_contract", str(reason))

# in-progress discovery sidecar never reused
dp = tmp / "harvest.discovery.json"
spike.write_discovery_checkpoint(dp, store_url="https://x/store/a-1", store_id="1",
                                 items=sel_items, discovery=None, state="in_progress")
got = spike.load_completed_discovery_checkpoint(dp, store_url="https://x/store/a-1", store_id="1")
check("in_progress discovery sidecar never reused", got[0] is None and got[2] == "discovery_checkpoint_not_complete", str(got[2]))

# duplicate result / retry does not clobber a success
by_id = {}
spike.upsert_capture_result(by_id, {"item_id": "1", "item_page": {"a": 1}, "sections": ["Tacos"]})
spike.upsert_capture_result(by_id, {"item_id": "1", "item_page": None, "error": "http_error"})
check("later failure cannot clobber a stored success", by_id["1"]["item_page"] == {"a": 1}, str(by_id["1"].get("error")))
check("no duplicate records per item id", len(by_id) == 1)

# top-level complete flag is derived
doc = json.loads(cp.read_text())
check("top-level complete derived from harvest.state",
      doc["complete"] is False and doc["harvest"]["state"] == "in_progress", str(doc["complete"]))

print("\n%d/%d checks passed" % (sum(1 for _, ok, _ in results if ok), len(results)))
