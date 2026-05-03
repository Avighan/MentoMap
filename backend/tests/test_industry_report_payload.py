"""Tests for the Phase B payload bridge — get_industry_report_config +
build_industry_report_payload — that wires IndustryReportEngine into
executive_ux composition.

Phase A's IndustryReportEngine takes a dict-state and returns a bundle.
The payload bridge reads simulation_config.industry_report from the game,
synthesises the engine state dict from runtime state attrs, calls the
engine, and returns a None-or-payload result so executive_ux can compose
it like every other subsystem.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.industry_report_engine import (
    get_industry_report_config,
    build_industry_report_payload,
)


class _State:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


_GAME_WITH_REPORT = {
    "simulation_config": {
        "industry_report": {
            "title": "Atlas Industry Pulse",
            "business_model": "saas_smb",
            "kpis": [
                {"id": "nps", "label": "NPS", "source": "nps", "prior_source": "prior_nps", "format": "int"},
            ],
        }
    }
}


def test_get_config_returns_config_when_present():
    cfg = get_industry_report_config(_GAME_WITH_REPORT)
    assert cfg is not None
    assert cfg["business_model"] == "saas_smb"


def test_get_config_returns_none_when_missing():
    assert get_industry_report_config({"game_type": "rounds"}) is None
    assert get_industry_report_config({"simulation_config": {}}) is None


def test_payload_returns_none_when_no_config():
    state = _State()
    assert build_industry_report_payload(state, {"game_type": "rounds"}) is None


def test_payload_uses_runtime_industry_state_when_present():
    """When state._industry_runtime is populated, payload comes from there."""
    runtime = {
        "market": {
            "firms": [
                {"name": "PlayerCo", "share_pct": 35.0},
                {"name": "Atlas", "share_pct": 30.0},
            ],
            "segments": [{"name": "SMB", "current_size": 100, "prior_size": 95}],
        },
        "finance": {"revenue": 12000, "gross_margin": 0.62, "net_income": 1500},
        "prior_market_share": {"PlayerCo": 32.0, "Atlas": 31.0},
        "prior_finance": {"revenue": 10000, "gross_margin": 0.60, "net_income": 1200},
        "nps": 42,
        "prior_nps": 35,
    }
    state = _State(_industry_runtime=runtime)
    payload = build_industry_report_payload(state, _GAME_WITH_REPORT)
    assert payload is not None
    assert payload["title"] == "Atlas Industry Pulse"
    assert payload["business_model"] == "saas_smb"
    rows = payload["report"]["market_share_table"]
    assert any(r["firm"] == "PlayerCo" and abs(r["delta_vs_prior"] - 3.0) < 0.01 for r in rows)
    grid = payload["report"]["kpi_grid"]
    assert any(k["id"] == "nps" and k["value"] == 42 and k["vs_prior"] == 7 for k in grid)


def test_payload_falls_back_to_minimal_when_no_runtime():
    """No _industry_runtime attr → return a payload with empty market_share_table
    and zero deltas (do not crash, do not return None)."""
    state = _State()
    payload = build_industry_report_payload(state, _GAME_WITH_REPORT)
    assert payload is not None
    assert payload["business_model"] == "saas_smb"
    assert isinstance(payload["report"]["market_share_table"], list)
    # No firms declared yet → empty table is acceptable
    assert payload["report"]["market_share_table"] == []


def test_payload_passes_period_label_through():
    state = _State(_industry_runtime={"market": {"firms": []}}, _finance_period_index=2)
    payload = build_industry_report_payload(state, _GAME_WITH_REPORT)
    # Either the engine's period_label is set, or payload exposes period_index
    assert "period_label" in payload["report"] or payload.get("period_index") == 2


def test_payload_does_not_mutate_state():
    runtime = {"market": {"firms": [{"name": "A", "share_pct": 10.0}]}}
    state = _State(_industry_runtime=runtime)
    import copy
    snap = copy.deepcopy(runtime)
    build_industry_report_payload(state, _GAME_WITH_REPORT)
    assert runtime == snap
