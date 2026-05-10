"""Tests for IndustryReportEngine (Phase A.2 of HBR/CapSim parity uplift).

Pure-function engine that produces an Atlas Industry Pulse report
between rounds — market share with deltas, financial summary, KPI
grid, and segment growth — without mutating state.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.industry_report_engine import IndustryReportEngine


def make_state():
    return {
        "market": {
            "firms": [
                {"name": "PlayerCo", "share_pct": 35.0},
                {"name": "CompA", "share_pct": 30.0},
                {"name": "CompB", "share_pct": 20.0},
            ],
            "segments": [
                {"name": "Enterprise", "current_size": 110, "prior_size": 100},
                {"name": "SMB", "current_size": 95, "prior_size": 100},
            ],
        },
        "finance": {"revenue": 12000, "gross_margin": 0.62, "net_income": 1500},
        "prior_market_share": {"PlayerCo": 32.0, "CompA": 31.0, "CompB": 21.0},
        "prior_finance": {"revenue": 10000, "gross_margin": 0.60, "net_income": 1200},
    }


def test_market_share_includes_delta_vs_prior():
    eng = IndustryReportEngine()
    rep = eng.build_report(make_state())
    rows = rep["market_share_table"]
    player = next(r for r in rows if r["firm"] == "PlayerCo")
    assert abs(player["delta_vs_prior"] - 3.0) < 0.01


def test_financial_summary_computes_deltas():
    eng = IndustryReportEngine()
    rep = eng.build_report(make_state())
    fin = rep["financial_summary"]
    assert fin["revenue"] == 12000
    assert fin["revenue_delta"] == 2000


def test_kpi_grid_uses_definitions():
    eng = IndustryReportEngine()
    state = make_state()
    state["nps"] = 42
    state["prior_nps"] = 35
    state["__kpi_defs"] = [
        {"id": "nps", "label": "NPS", "source": "nps", "prior_source": "prior_nps", "format": "int"}
    ]
    rep = eng.build_report(state)
    grid = rep["kpi_grid"]
    assert len(grid) >= 1
    nps = next(k for k in grid if k["id"] == "nps")
    assert nps["value"] == 42
    assert nps["vs_prior"] == 7
    assert nps["sentiment"] == "positive"


def test_segment_growth_pct():
    eng = IndustryReportEngine()
    rep = eng.build_report(make_state())
    segs = rep["segment_growth"]
    ent = next(s for s in segs if s["segment"] == "Enterprise")
    smb = next(s for s in segs if s["segment"] == "SMB")
    assert abs(ent["growth_pct"] - 10.0) < 0.01
    assert abs(smb["growth_pct"] + 5.0) < 0.01


def test_period_label_passes_through():
    eng = IndustryReportEngine()
    rep = eng.build_report(make_state(), period_label="Q3 FY26")
    assert rep["period_label"] == "Q3 FY26"


def test_handles_missing_prior_finance_gracefully():
    eng = IndustryReportEngine()
    state = make_state()
    state.pop("prior_finance")
    rep = eng.build_report(state)
    fin = rep["financial_summary"]
    assert fin["revenue"] == 12000
    assert fin["revenue_delta"] == 0  # no prior -> delta 0


def test_does_not_mutate_state():
    eng = IndustryReportEngine()
    state = make_state()
    import copy
    snapshot = copy.deepcopy(state)
    eng.build_report(state)
    assert state == snapshot


def test_kpi_grid_sentiment_negative_and_neutral():
    eng = IndustryReportEngine()
    state = make_state()
    state["a"] = 10
    state["prior_a"] = 20
    state["b"] = 5
    state["prior_b"] = 5
    state["__kpi_defs"] = [
        {"id": "a", "label": "A", "source": "a", "prior_source": "prior_a", "format": "int"},
        {"id": "b", "label": "B", "source": "b", "prior_source": "prior_b", "format": "int"},
    ]
    rep = eng.build_report(state)
    a = next(k for k in rep["kpi_grid"] if k["id"] == "a")
    b = next(k for k in rep["kpi_grid"] if k["id"] == "b")
    assert a["sentiment"] == "negative"
    assert b["sentiment"] == "neutral"
