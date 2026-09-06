"""
Market Engine — executive-tier market sizing / funnel / competitive-landscape
subsystem for simulation games.

Activated only when game JSON declares `simulation_config.market`. When absent,
`build_market_payload` returns None and existing games are unaffected.

Schema (derived from games/series-a-founders-journey.json, a real committed
example):

    simulation_config.market = {
      "tam_usd": 8000000000,
      "sam_usd": 1200000000,
      "som_usd": 80000000,
      "funnel_stages": [
        {"name": "Visitors", "count": 24000},
        {"name": "Sign-ups", "count": 1800},
        ...
      ],
      "competitors": [
        {"name": "BigCo Analytics", "share_pct": 38, "innovation_score": 55},
        {"name": "Mentolytics (you)", "share_pct": 4, "innovation_score": 78},
        ...
      ],
      "channels": [
        {"name": "Outbound", "cost_per_lead": 80, "conv_pct": 4},
        ...
      ]
    }

Runtime overrides (all optional, set via choice effects elsewhere):
    state._market_competitor_shares: {competitor_name: new_share_pct}
    state._market_channel_spend:     {channel_name: usd_spent}

All helpers are pure functions of (state, game) — they read state, never
mutate it.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _get(state: Any, key: str, default: Any = None) -> Any:
    if isinstance(state, dict):
        return state.get(key, default)
    return getattr(state, key, default)


# ────────────────────────────────────────────────────────────────────
# Schema activation
# ────────────────────────────────────────────────────────────────────

def get_market_config(game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return the market block, or None if the game doesn't declare one."""
    sim = (game or {}).get("simulation_config") or {}
    cfg = sim.get("market")
    if not isinstance(cfg, dict):
        return None
    return cfg


# ────────────────────────────────────────────────────────────────────
# Sub-computations
# ────────────────────────────────────────────────────────────────────

def compute_market_sizing(state: Any, cfg: Dict[str, Any]) -> Dict[str, Any]:
    """TAM/SAM/SOM with best-effort capture % from current traction."""
    tam = float(cfg.get("tam_usd", 0) or 0)
    sam = float(cfg.get("sam_usd", 0) or 0)
    som = float(cfg.get("som_usd", 0) or 0)
    # Best-effort revenue signal: prefer arr, then annualised monthly revenue.
    arr = float(_get(state, "arr", 0) or 0)
    if not arr:
        mrr = float(_get(state, "monthly_revenue", 0) or 0)
        arr = mrr * 12.0
    captured_pct_of_som = (arr / som * 100.0) if som else None
    return {
        "tam_usd": tam,
        "sam_usd": sam,
        "som_usd": som,
        "sam_pct_of_tam": (sam / tam * 100.0) if tam else None,
        "som_pct_of_sam": (som / sam * 100.0) if sam else None,
        "current_arr_usd": arr,
        "captured_pct_of_som": captured_pct_of_som,
    }


def compute_funnel(cfg: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """Attach stage-over-stage conversion % to each authored funnel stage."""
    stages = cfg.get("funnel_stages")
    if not isinstance(stages, list) or not stages:
        return None
    out = []
    prev_count: Optional[float] = None
    for s in stages:
        count = float(s.get("count", 0) or 0)
        conv_pct = (count / prev_count * 100.0) if prev_count else None
        out.append({
            "name": s.get("name", "Stage"),
            "count": int(count),
            "conversion_from_prev_pct": conv_pct,
        })
        prev_count = count or prev_count
    if len(out) >= 2 and out[0]["count"]:
        out[-1]["overall_conversion_pct"] = out[-1]["count"] / out[0]["count"] * 100.0
    return out


def compute_competitive_landscape(state: Any, cfg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Merge authored competitor shares with any runtime overrides."""
    competitors = cfg.get("competitors")
    if not isinstance(competitors, list) or not competitors:
        return None
    overrides = _get(state, "_market_competitor_shares", {}) or {}
    out = []
    player_share = None
    for c in competitors:
        name = c.get("name", "Competitor")
        share = float(overrides.get(name, c.get("share_pct", 0)) or 0)
        is_player = "(you)" in name.lower() or bool(c.get("is_player"))
        if is_player:
            player_share = share
        out.append({
            "name": name,
            "share_pct": share,
            "innovation_score": c.get("innovation_score"),
            "is_player": is_player,
        })
    out.sort(key=lambda r: r["share_pct"], reverse=True)
    total_share = sum(r["share_pct"] for r in out)
    return {
        "competitors": out,
        "player_share_pct": player_share,
        "market_rank": (next((i + 1 for i, r in enumerate(out) if r["is_player"]), None)),
        "unaccounted_share_pct": max(0.0, 100.0 - total_share),
    }


def compute_channel_efficiency(state: Any, cfg: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """Estimate leads/customers per authored channel given spend (default $10k/channel)."""
    channels = cfg.get("channels")
    if not isinstance(channels, list) or not channels:
        return None
    spend_overrides = _get(state, "_market_channel_spend", {}) or {}
    out = []
    for ch in channels:
        name = ch.get("name", "Channel")
        cost_per_lead = float(ch.get("cost_per_lead", 0) or 0)
        conv_pct = float(ch.get("conv_pct", 0) or 0)
        spend = float(spend_overrides.get(name, 10000) or 0)
        leads = (spend / cost_per_lead) if cost_per_lead else 0.0
        customers = leads * (conv_pct / 100.0)
        out.append({
            "name": name,
            "spend_usd": spend,
            "cost_per_lead": cost_per_lead,
            "conv_pct": conv_pct,
            "estimated_leads": round(leads, 1),
            "estimated_customers": round(customers, 2),
            "estimated_cac": round(spend / customers, 2) if customers else None,
        })
    return out


# ────────────────────────────────────────────────────────────────────
# Public payload builder
# ────────────────────────────────────────────────────────────────────

def build_market_payload(state: Any, game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """One-shot builder used by the UX enrichment layer. Returns None when
    market isn't configured for this game."""
    cfg = get_market_config(game)
    if not cfg:
        return None
    payload: Dict[str, Any] = {
        "sizing": None,
        "funnel": None,
        "competitive_landscape": None,
        "channels": None,
    }
    try:
        payload["sizing"] = compute_market_sizing(state, cfg)
    except Exception:
        pass
    try:
        payload["funnel"] = compute_funnel(cfg)
    except Exception:
        pass
    try:
        payload["competitive_landscape"] = compute_competitive_landscape(state, cfg)
    except Exception:
        pass
    try:
        payload["channels"] = compute_channel_efficiency(state, cfg)
    except Exception:
        pass
    return payload
