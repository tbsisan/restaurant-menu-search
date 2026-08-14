"""Regression coverage for the DoorDash harvest artifact contract.

Run from the repository root with::

    pytest external-data/scripts/test_doordash_harvest.py

The tests use fakes for browser control and recorded public menu data, so they
exercise the artifact contract without making a live DoorDash request.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
import requests


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "external-data" / "scripts"
FIXTURE_PATH = SCRIPTS / "fixtures" / "doordash-china-1-item-page.json"


def load_module(filename: str, name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


spike = load_module("spike_doordash_network_capture.py", "doordash_harvest_spike")
normalizer = load_module("normalize_menu_sizes.py", "doordash_size_normalizer")
item_parser = load_module("parse_doordash_itempage.py", "doordash_item_parser")


@pytest.fixture(autouse=True)
def avoid_real_waits(monkeypatch: pytest.MonkeyPatch) -> None:
    """The scraper's pacing is not under test; keep its state tests fast."""
    monkeypatch.setattr(spike.time, "sleep", lambda *_: None)


@pytest.fixture
def recorded_item_page() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


class FetchClient:
    def __init__(self, response):
        self.response = response

    def evaluate(self, tab_id, expression, timeout=60):
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def item_page_response(page: dict) -> dict:
    return {"status": 200, "body": json.dumps({"data": {"itemPage": page}})}


def fetch(response, item_id="42") -> dict:
    return spike.fetch_item_page(FetchClient(response), "tab", "store", item_id, "query")


@pytest.mark.parametrize(
    ("response", "expected_ok", "expected_kind"),
    [
        (item_page_response({"itemHeader": {"id": "42"}, "optionLists": []}), True, "success"),
        ({"status": 503, "body": "upstream unavailable"}, False, "http_error"),
        ({"status": 200, "body": json.dumps({"errors": [{"message": "boom"}]})}, False, "graphql_errors"),
        ({"status": 200, "body": "<html>not JSON"}, False, "response_not_json"),
        ({"status": 200, "body": json.dumps(["not a GraphQL object"])}, False, "malformed_graphql_payload"),
        ({"status": 200, "body": json.dumps({"data": {}})}, False, "missing_item_page"),
        ({"status": 200, "body": json.dumps({"data": {"itemPage": {}}})}, False, "malformed_item_page"),
        (
            {"status": 200, "body": json.dumps({"data": {"itemPage": {"itemHeader": {"id": "other"}}}})},
            False,
            "item_identity_mismatch",
        ),
        ({"fetch_error": "TypeError: failed"}, False, "network_fetch_error"),
        ({"status": "200", "body": "{}"}, False, "malformed_response_wrapper"),
        (requests.HTTPError("tab gone"), False, "camofox_evaluate_error"),
        ("not a response wrapper", False, "camofox_evaluate_invalid_result"),
    ],
    ids=[
        "success",
        "http_error",
        "graphql_errors",
        "response_not_json",
        "malformed_graphql_payload",
        "missing_item_page",
        "malformed_item_page",
        "item_identity_mismatch",
        "network_fetch_error",
        "malformed_wrapper",
        "camofox_evaluate_error",
        "camofox_invalid_result",
    ],
)
def test_fetch_item_page_diagnostics(response, expected_ok, expected_kind) -> None:
    result = fetch(response)
    diagnostic = result["diagnostic"]
    actual_kind = diagnostic.get("kind") or diagnostic.get("outcome")
    assert result["ok"] is expected_ok
    assert actual_kind == expected_kind


def test_fetch_item_page_accepts_trimmed_recorded_payload(recorded_item_page: dict) -> None:
    item_id = recorded_item_page["itemHeader"]["id"]
    result = fetch(item_page_response(recorded_item_page), item_id=item_id)

    assert result["ok"] is True
    assert result["item_page"] == recorded_item_page
    assert result["diagnostic"]["response_item_id"] == item_id
    assert result["item_page"]["optionLists"][0]["name"] == "Rice Choice"


@pytest.mark.parametrize(
    ("selected_items", "results", "discovery", "selection", "finished", "expected_state", "expected_reason"),
    [
        (
            [{"item_id": "1"}, {"item_id": "2"}],
            [{"item_id": "1", "item_page": {}}, {"item_id": "2", "item_page": {}}],
            {"status": "complete", "stop_reason": "bottom_stable"},
            {"source": "live_discovery", "sample_per_section": None, "item_limit": None},
            True,
            "complete",
            None,
        ),
        (
            [{"item_id": "1"}, {"item_id": "2"}],
            [{"item_id": "1", "item_page": {}}],
            {"status": "complete", "stop_reason": "bottom_stable"},
            {"source": "live_discovery", "sample_per_section": None, "item_limit": None},
            True,
            "incomplete",
            "item_page_captures_pending",
        ),
        (
            [{"item_id": "1"}],
            [{"item_id": "1", "item_page": None, "error": "http_error"}],
            {"status": "complete", "stop_reason": "bottom_stable"},
            {"source": "live_discovery", "sample_per_section": None, "item_limit": None},
            True,
            "incomplete",
            "item_page_failures",
        ),
        (
            [{"item_id": "1"}],
            [{"item_id": "1", "item_page": {}}],
            {"status": "incomplete", "stop_reason": "scroll_limit_reached"},
            {"source": "live_discovery", "sample_per_section": None, "item_limit": None},
            True,
            "incomplete",
            "discovery_scroll_limit_reached",
        ),
        (
            [{"item_id": "1"}],
            [{"item_id": "1", "item_page": {}}],
            {"status": "complete", "stop_reason": "bottom_stable"},
            {"source": "live_discovery", "sample_per_section": None, "item_limit": 1},
            True,
            "incomplete",
            "item_selection_limited",
        ),
        (
            [{"item_id": "1"}],
            [{"item_id": "1", "item_page": {}}],
            {"status": "complete", "stop_reason": "bottom_stable"},
            {"source": "live_discovery", "sample_per_section": 3, "item_limit": None},
            True,
            "incomplete",
            "item_selection_sampled",
        ),
        (
            [{"item_id": "1"}],
            [{"item_id": "1", "item_page": {}}],
            {"status": "complete", "stop_reason": "bottom_stable"},
            {"source": "items_file", "sample_per_section": None, "item_limit": None},
            True,
            "incomplete",
            "item_selection_not_live_verified",
        ),
        (
            [],
            [],
            {"status": "complete", "stop_reason": "bottom_stable"},
            {"source": "live_discovery", "sample_per_section": None, "item_limit": None},
            True,
            "incomplete",
            "no_items_selected",
        ),
    ],
    ids=["clean", "pending", "failed_capture", "scroll_cap", "limit", "sample", "items_file", "empty_selection"],
)
def test_harvest_status_completeness_gates(
    selected_items, results, discovery, selection, finished, expected_state, expected_reason
) -> None:
    status = spike.build_harvest_status(
        selected_items=selected_items,
        results=results,
        discovery=discovery,
        selection=selection,
        finished=finished,
    )
    assert status["schema_version"] == 2
    assert status["state"] == expected_state
    if expected_reason is None:
        assert status["reasons"] == []
    else:
        assert expected_reason in status["reasons"]


class ScriptedDiscoveryClient:
    """Small fake of the browser calls made by ``collect_items``."""

    def __init__(self, *, cards, problem=None, grows=False, at_bottom=True, die_after=None):
        self.cards = cards
        self.problem = problem
        self.grows = grows
        self.at_bottom = at_bottom
        self.die_after = die_after
        self.calls = 0
        self.current_count = cards

    def evaluate(self, tab_id, expression, timeout=60):
        self.calls += 1
        if self.die_after is not None and self.calls > self.die_after:
            raise requests.HTTPError("tab disappeared")
        if expression == spike.DISMISS_PROBE_JS:
            return {"visible": False}
        if expression == spike.DISCOVERY_PAGE_STATE_JS:
            return {
                "ready_state": "complete",
                "rendered_menu_card_count": self.current_count,
                "visible_menu_card_count": self.current_count,
                "category_headings": ["Tacos"],
                "problem_signals": [self.problem] if self.problem else [],
            }
        if expression == spike.RESET_COLLECTION_JS:
            return {"url": "https://www.doordash.com/store/test-store-1/", "reset": True}
        if expression == spike.COLLECT_STEP_JS:
            if self.grows:
                self.current_count += 3
            return {"total": self.current_count, "eligible_cards_in_view": self.current_count, "selector_counts": {}}
        if expression.startswith("(function(){\n  window.scrollBy"):
            return {"y": 0, "h": 800, "viewport": 800, "at_bottom": self.at_bottom}
        if expression == spike.COLLECTED_JS:
            return [
                {"item_id": str(index), "section": "Tacos", "sections": ["Tacos"]}
                for index in range(self.current_count)
            ]
        return None


@pytest.mark.parametrize(
    ("client", "max_scrolls", "expected_status", "expected_stop"),
    [
        (ScriptedDiscoveryClient(cards=5), 60, "complete", "bottom_stable"),
        (ScriptedDiscoveryClient(cards=0, problem="verify you are human"), 60, "incomplete", "page_problem_signaled"),
        (ScriptedDiscoveryClient(cards=3, grows=True, at_bottom=False), 6, "incomplete", "scroll_limit_reached"),
    ],
    ids=["small_menu", "bot_check", "growing_at_scroll_cap"],
)
def test_discovery_outcomes(client, max_scrolls, expected_status, expected_stop) -> None:
    items, discovery = spike.collect_items(client, "tab", max_scrolls=max_scrolls)
    assert discovery["status"] == expected_status
    assert discovery["stop_reason"] == expected_stop
    if expected_stop == "page_problem_signaled":
        assert items == []
        assert discovery["page_usable"] == "no"
    else:
        assert items


def test_browser_loss_during_discovery_returns_incomplete_record() -> None:
    checkpoints: list[list[dict]] = []
    items, discovery = spike.collect_items(
        ScriptedDiscoveryClient(cards=4, grows=True, die_after=6),
        "tab",
        max_scrolls=60,
        checkpoint_callback=lambda observed: checkpoints.append(list(observed)),
    )
    assert items
    assert discovery["status"] == "incomplete"
    assert discovery["stop_reason"] == "browser_lost_during_discovery"
    assert discovery["browser_error"]["kind"] == "camofox_evaluate_error"
    assert checkpoints[-1] == items


def test_early_browser_loss_checkpoints_an_empty_discovery() -> None:
    checkpoints: list[list[dict]] = []
    items, discovery = spike.collect_items(
        ScriptedDiscoveryClient(cards=0, die_after=1),
        "tab",
        checkpoint_callback=lambda observed: checkpoints.append(list(observed)),
    )

    assert items == []
    assert discovery["status"] == "incomplete"
    assert discovery["stop_reason"] == "browser_lost_during_discovery"
    assert checkpoints == [[]]


def test_every_retryable_diagnostic_gets_one_more_attempt() -> None:
    responses = [
        {"status": 503, "body": "upstream unavailable"},
        {"fetch_error": "TypeError: failed"},
        requests.HTTPError("tab gone"),
        "not a response wrapper",
    ]
    diagnostics = [fetch(response)["diagnostic"] for response in responses]
    assert all(
        spike.should_retry_item_page_capture(diagnostic, attempt=1)
        for diagnostic in diagnostics
        if diagnostic["retryable"]
    )
    assert not any(spike.should_retry_item_page_capture(diagnostic, attempt=2) for diagnostic in diagnostics)


def test_ratings_file_only_overrides_present_non_null_values() -> None:
    entries = [
        {"item_id": "inline-only", "like_percent": 92, "like_review_count": 48},
        {"item_id": "supplemented", "like_percent": 84, "like_review_count": 11},
        {"item_id": "partial", "like_percent": 77, "like_review_count": 9},
    ]
    ratings = [
        {"item_id": "supplemented", "like_percent": 95, "like_review_count": 20},
        {"item_id": "partial", "like_percent": None, "like_review_count": 13},
        {"item_id": "not-in-harvest", "like_percent": 100, "like_review_count": 1},
    ]

    merged = item_parser.merge_card_ratings(entries, ratings)

    assert merged[0] == entries[0]
    assert merged[1]["like_percent"] == 95
    assert merged[1]["like_review_count"] == 20
    assert merged[2]["like_percent"] == 77
    assert merged[2]["like_review_count"] == 13


def test_sample_per_section_uses_all_memberships_without_duplicate_fetches() -> None:
    items = [
        {"item_id": "taco", "section": "Tacos", "sections": ["Tacos"]},
        {"item_id": "featured", "section": "Tacos", "sections": ["Tacos", "Most Ordered"]},
        {"item_id": "drink", "section": "Drinks", "sections": ["Drinks"]},
    ]

    sampled, section_count = spike.sample_items_by_section(items, sample_per_section=1, sample_seed=7)

    assert section_count == 3
    assert "featured" in {item["item_id"] for item in sampled}
    assert len(sampled) == len({item["item_id"] for item in sampled})


def test_resume_rejects_mismatched_or_precontract_checkpoints(tmp_path: Path) -> None:
    selection = {"source": "live_discovery", "sample_per_section": None, "sample_seed": None, "item_limit": None}
    selected_items = [
        {"item_id": "1", "section": "Tacos", "sections": ["Tacos"]},
        {"item_id": "2", "section": "Tacos", "sections": ["Tacos", "Most Ordered"]},
    ]
    capture_path = tmp_path / "harvest.json"
    spike.write_harvest(
        capture_path,
        "https://www.doordash.com/store/test-store-1/",
        "1",
        [{"item_id": "1", "item_page": {"itemHeader": {}}, "menu_position": 0}],
        selected_items=selected_items,
        discovery={"status": "complete", "stop_reason": "bottom_stable"},
        selection=selection,
        finished=False,
    )

    previous, reason = spike.load_previous(
        capture_path,
        store_url="https://www.doordash.com/store/test-store-1/",
        store_id="1",
        selection=selection,
        selected_items=selected_items,
    )
    assert set(previous) == {"1"}
    assert reason is None

    written = json.loads(capture_path.read_text(encoding="utf-8"))
    assert written["complete"] is False
    assert written["harvest"]["state"] == "in_progress"

    _, reason = spike.load_previous(
        capture_path,
        store_url="https://www.doordash.com/store/test-store-1/",
        store_id="other-store",
        selection=selection,
        selected_items=selected_items,
    )
    assert reason == "checkpoint_store_id_mismatch"

    _, reason = spike.load_previous(
        capture_path,
        store_url="https://www.doordash.com/store/a-different-store-1/",
        store_id="1",
        selection=selection,
        selected_items=selected_items,
    )
    assert reason == "checkpoint_store_url_mismatch"

    _, reason = spike.load_previous(
        capture_path,
        store_url="https://www.doordash.com/store/test-store-1/",
        store_id="1",
        selection={**selection, "item_limit": 3},
        selected_items=selected_items,
    )
    assert reason == "checkpoint_selection_mismatch"

    legacy_path = tmp_path / "legacy.json"
    legacy_path.write_text(json.dumps({"source_url": "https://www.doordash.com/store/test-store-1/", "store_id": "1"}))
    _, reason = spike.load_previous(
        legacy_path,
        store_url="https://www.doordash.com/store/test-store-1/",
        store_id="1",
        selection=selection,
        selected_items=selected_items,
    )
    assert reason == "checkpoint_has_no_compatible_harvest_contract"


def test_in_progress_discovery_sidecar_is_not_reused(tmp_path: Path) -> None:
    sidecar = tmp_path / "harvest.discovery.json"
    spike.write_discovery_checkpoint(
        sidecar,
        store_url="https://www.doordash.com/store/test-store-1/",
        store_id="1",
        items=[{"item_id": "1"}],
        discovery=None,
        state="in_progress",
    )
    items, discovery, reason = spike.load_completed_discovery_checkpoint(
        sidecar,
        store_url="https://www.doordash.com/store/test-store-1/",
        store_id="1",
    )
    assert items is None
    assert discovery is None
    assert reason == "discovery_checkpoint_not_complete"


def test_successful_result_is_not_clobbered_by_later_failure() -> None:
    results_by_id = {}
    spike.upsert_capture_result(results_by_id, {"item_id": "1", "item_page": {"itemHeader": {"id": "1"}}})
    spike.upsert_capture_result(results_by_id, {"item_id": "1", "item_page": None, "error": "http_error"})
    assert list(results_by_id) == ["1"]
    assert results_by_id["1"]["item_page"] == {"itemHeader": {"id": "1"}}


def test_parser_cli_preserves_duplicate_category_memberships(tmp_path: Path, recorded_item_page: dict) -> None:
    source = tmp_path / "duplicate-category-harvest.json"
    output = tmp_path / "parsed.json"
    source.write_text(json.dumps({
        "source_url": "https://www.doordash.com/store/test-store-1/",
        "items": [
            {
                "item_id": "source-a",
                "section": "Tacos",
                "sections": ["Tacos", "Most Ordered"],
                "item_page": recorded_item_page,
            },
            {
                "item_id": "source-b",
                "section": "Tacos",
                "sections": ["Tacos"],
                "item_page": recorded_item_page,
            },
        ],
    }), encoding="utf-8")

    subprocess.run(
        [sys.executable, str(SCRIPTS / "parse_doordash_itempage.py"), str(source), str(output)],
        check=True,
        capture_output=True,
        text=True,
    )
    parsed = json.loads(output.read_text(encoding="utf-8"))
    sections = {entry["section"]: entry["items"] for entry in parsed["menu_sections"]}

    assert set(sections) == {"Tacos", "Most Ordered"}
    assert {item["source_item_id"] for item in sections["Tacos"]} == {"source-a", "source-b"}
    assert [item["source_item_id"] for item in sections["Most Ordered"]] == ["source-a"]
    assert sections["Most Ordered"][0]["section_memberships"] == ["Tacos", "Most Ordered"]


def test_size_normalizer_preserves_source_lineage_and_memberships() -> None:
    merged = normalizer.merge_group(
        [
            {"title": "Small Nachos", "source_item_id": "small", "section_memberships": ["Appetizers"], "price_min": 5.0, "options": []},
            {"title": "Large Nachos", "source_item_id": "large", "section_memberships": ["Appetizers", "Most Ordered"], "price_min": 8.0, "options": []},
        ],
        "Nachos",
        ["Small", "Large"],
    )
    assert merged["source_item_ids"] == ["small", "large"]
    assert merged["section_memberships"] == ["Appetizers", "Most Ordered"]
