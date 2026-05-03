"""Industry Report Engine — between-rounds Atlas Industry Pulse.

Phase A.2 of the HBR/CapSim parity uplift. Mimics CapSim's Capstone
Courier: a digestible report shown to the player between rounds that
summarises market share movement, financial performance, segment
growth, and a small grid of KPIs.

The engine is a pure function over a state dict — it never mutates
its input. State shape it consumes::

    {
      "market": {
        "firms":    [{"name": str, "share_pct": float}, ...],
        "segments": [{"name": str, "current_size": num, "prior_size": num}, ...]
      },
      "finance":             {"revenue": num, "gross_margin": num, "net_income": num, ...},
      "prior_market_share":  {firm_name: prior_share_pct, ...},
      "prior_finance":       {"revenue": num, ...},
      "__kpi_defs":          [{"id", "label", "source", "prior_source", "format"}, ...],
      "exec_quote":          optional str
    }

Output bundle::

    {
      "period_label":        str,
      "market_share_table":  [{"firm", "share_pct", "delta_vs_prior"}, ...],
      "financial_summary":   {"revenue", "revenue_delta",
                              "gross_margin", "gross_margin_delta",
                              "net_income",  "net_income_delta"},
      "kpi_grid":            [{"id", "label", "value", "vs_prior", "sentiment", "format"}, ...],
      "segment_growth":      [{"segment", "growth_pct", "current_size", "prior_size"}, ...],
      "exec_quote":          str | None
    }

Pure stdlib. Not yet registered in engines/__init__.py — wiring lands
in a later phase when callers in app.py adopt it.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


_FINANCE_KEYS = ("revenue", "gross_margin", "net_income")


def _is_numeric(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _get_dotted(source: dict, path: str, default: Any = None) -> Any:
    """Read a dotted path from a dict; return ``default`` if any segment is missing."""
    if not path or not isinstance(source, dict):
        return default
    cursor: Any = source
    for key in path.split("."):
        if not isinstance(cursor, dict) or key not in cursor:
            return default
        cursor = cursor[key]
    return cursor


def _sentiment(delta: Any) -> str:
    if not _is_numeric(delta):
        return "neutral"
    if delta > 0:
        return "positive"
    if delta < 0:
        return "negative"
    return "neutral"


class IndustryReportEngine:
    """Builds an HBR/CapSim-style industry pulse report between rounds.

    Reads finance/market/org state plus competitor positions, produces a
    bundle of 'segments' the player consumes between rounds:
      - market_share_table: list of {firm, share_pct, delta_vs_prior}
      - financial_summary: revenue, gross_margin, net_income for player firm
      - kpi_grid: list of {label, value, vs_prior, sentiment}
      - segment_growth: list of {segment, growth_pct}
      - exec_quote: optional commentary string

    Pure function — does not mutate state.
    """

    # ------------------------------------------------------------------ public

    def build_report(self, state: dict, period_label: str = "Q1") -> dict:
        """Build report dict with keys above.

        Reads from ``state`` without mutating it. Missing optional inputs
        degrade gracefully (deltas of 0, empty lists, etc.).
        """
        state = state or {}
        kpi_defs = state.get("__kpi_defs", []) or []

        return {
            "period_label": period_label,
            "market_share_table": self._market_share_table(state),
            "financial_summary": self._financial_summary(state),
            "kpi_grid": self._kpi_grid(state, kpi_defs),
            "segment_growth": self._segment_growth(state),
            "exec_quote": state.get("exec_quote"),
        }

    # ------------------------------------------------------------------ market share

    def _market_share_table(self, state: dict) -> list:
        """From ``state['market']['firms']`` compute share + delta vs prior."""
        market = state.get("market") or {}
        firms = market.get("firms") or []
        prior = state.get("prior_market_share") or {}

        rows: list = []
        for firm in firms:
            if not isinstance(firm, dict):
                continue
            name = firm.get("name")
            share = firm.get("share_pct", 0.0)
            if not _is_numeric(share):
                share = 0.0
            prior_share = prior.get(name)
            if _is_numeric(prior_share):
                delta = float(share) - float(prior_share)
            else:
                delta = 0.0
            rows.append(
                {
                    "firm": name,
                    "share_pct": float(share),
                    "delta_vs_prior": float(delta),
                }
            )
        return rows

    # ------------------------------------------------------------------ finance

    def _financial_summary(self, state: dict) -> dict:
        """From ``state['finance']`` extract canonical fields and deltas vs prior."""
        finance = state.get("finance") or {}
        prior = state.get("prior_finance") or {}

        out: dict = {}
        for key in _FINANCE_KEYS:
            value = finance.get(key, 0)
            if not _is_numeric(value):
                value = 0
            prior_value = prior.get(key)
            if _is_numeric(prior_value):
                delta = value - prior_value
            else:
                delta = 0
            out[key] = value
            out[f"{key}_delta"] = delta
        return out

    # ------------------------------------------------------------------ kpi grid

    def _kpi_grid(self, state: dict, kpi_defs: list) -> list:
        """Resolve each kpi definition against state.

        ``kpi_defs`` is a list of dicts ``{id, label, source, prior_source, format}``
        where ``source`` (and optional ``prior_source``) are dotted paths into
        ``state``. Definitions whose ``source`` does not resolve are omitted —
        an undefined KPI must not crash the report.
        """
        grid: list = []
        for kpi in kpi_defs or []:
            if not isinstance(kpi, dict):
                continue
            kid = kpi.get("id")
            source = kpi.get("source")
            if not kid or not source:
                continue
            value = _get_dotted(state, source, default=None)
            if value is None:
                # source path missing — skip rather than crash
                continue

            prior_source = kpi.get("prior_source")
            prior_value = _get_dotted(state, prior_source, default=None) if prior_source else None
            if _is_numeric(value) and _is_numeric(prior_value):
                vs_prior: Any = value - prior_value
            else:
                vs_prior = 0

            grid.append(
                {
                    "id": kid,
                    "label": kpi.get("label", kid),
                    "value": value,
                    "vs_prior": vs_prior,
                    "sentiment": _sentiment(vs_prior),
                    "format": kpi.get("format", "raw"),
                }
            )
        return grid

    # ------------------------------------------------------------------ segments

    def _segment_growth(self, state: dict) -> list:
        """From ``state['market']['segments']`` compute growth_pct vs prior_size.

        ``growth_pct = (current - prior) / prior * 100``. If prior is 0 or
        missing, growth is 0 (cannot meaningfully divide).
        """
        market = state.get("market") or {}
        segments = market.get("segments") or []

        out: list = []
        for seg in segments:
            if not isinstance(seg, dict):
                continue
            name = seg.get("name")
            current = seg.get("current_size", 0)
            prior = seg.get("prior_size", 0)
            if not _is_numeric(current):
                current = 0
            if not _is_numeric(prior):
                prior = 0
            if prior:
                growth = (float(current) - float(prior)) / float(prior) * 100.0
            else:
                growth = 0.0
            out.append(
                {
                    "segment": name,
                    "current_size": current,
                    "prior_size": prior,
                    "growth_pct": growth,
                }
            )
        return out


# ────────────────────────────────────────────────────────────────────
# Phase B payload bridge — opt-in via simulation_config.industry_report
# ────────────────────────────────────────────────────────────────────

def get_industry_report_config(game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return simulation_config.industry_report or None when not opted in.

    Schema:
        simulation_config:
          industry_report:
            title: "Atlas Industry Pulse"
            business_model: "saas_smb"     # for benchmark band lookup
            kpis:
              - {id: "nps", label: "NPS", source: "nps",
                 prior_source: "prior_nps", format: "int"}
    """
    sim = (game or {}).get("simulation_config") or {}
    cfg = sim.get("industry_report")
    if not isinstance(cfg, dict):
        return None
    return cfg


def build_industry_report_payload(state: Any, game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Build the between-rounds Atlas Industry Pulse payload.

    Reads:
      - state._industry_runtime: dict-state for IndustryReportEngine
        (market.firms, market.segments, finance, prior_market_share, etc.).
        Populated by core/rounds.py once the engine is wired into the loop.
      - state._finance_period_index: optional int for period label.
      - game.simulation_config.industry_report: KPI defs + title + biz model.

    Returns None when no industry_report config is declared. When configured
    but no runtime present yet (round 0), returns a payload whose engine
    output has empty market_share_table — the widget can still render the
    title/business_model strip.
    """
    cfg = get_industry_report_config(game)
    if not cfg:
        return None

    runtime = getattr(state, "_industry_runtime", None) or {}
    period_index = getattr(state, "_finance_period_index", None)

    # Bridge: inject __kpi_defs from cfg into the engine state if not present
    eng_state = dict(runtime) if isinstance(runtime, dict) else {}
    if "__kpi_defs" not in eng_state and isinstance(cfg.get("kpis"), list):
        eng_state["__kpi_defs"] = cfg["kpis"]

    period_label = cfg.get("period_label_template", "Q{n}").replace(
        "{n}", str(period_index) if period_index is not None else "1"
    )

    report = IndustryReportEngine().build_report(eng_state, period_label=period_label)

    payload: Dict[str, Any] = {
        "title": cfg.get("title", "Industry Pulse"),
        "business_model": cfg.get("business_model"),
        "report": report,
    }
    if period_index is not None:
        payload["period_index"] = period_index
    return payload
