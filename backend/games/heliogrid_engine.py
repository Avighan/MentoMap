"""
HelioGrid — Choose Your Customer — Tier C pilot game (continuous levers).

Unlike Dealcraft/Mumbai Manufacturer, there is no discrete choice list:
every quarter the player sets continuous levers (price, per-segment
discounts, sales allocation, headcount, comms/research/feature spend)
and the market resolves against four segments with different "wants"
and a rival that drifts toward whichever segment is in focus that
quarter. See `heliogrid.json`'s `resolution_config` for every constant
used below — nothing here is a hidden magic number.

Scale note (approximation, flagged per the pilot brief): the brief's
`units_sold = size * (fit/100) * (0.35 + 0.65*sales_intensity) *
comms_factor` is ported verbatim below, and segment `size` (700-1900)
is ported verbatim too. Taken completely literally at high fit/comms
that formula can sell more than 100% of a segment's `size` in a single
quarter, which — at this game's ~$100-200K unit prices — produces
quarterly revenue two to three orders of magnitude above the brief's
own scoring bands (`cumulative_profit` up to 2,500,000;
`cumulative_revenue` up to 18,000,000 across all 8 quarters combined).
`sales_intensity` and `comms_factor` were left for me to define (the
brief only says what they "derive from"), so the reconciling knob is
`resolution_config.quarterly_capture_rate`: a single scalar applied
uniformly to both the player's and the rival's unit counts before
revenue/cogs/opex, so it changes absolute scale without touching the
market-share *ratio* between the two, or the shape of any formula given
verbatim by the brief.

Formula choice — benchmark_scorecard, not expert_drift:
`expert_drift` (engines.decision_panel_engine.DecisionPanelEngine.
compute_drift) scores continuous controls by how far the player's value
sits from a single fixed "expert_pick" per control. That model fits a
slider-calibration exercise where the designer knows the one right
number for each dial. HelioGrid's levers have no such single ideal
value — a listPrice or a sales-allocation split that's excellent for
Campus Estates is mediocre for Installer Guild, and the "right" answer
is genuinely conditional on which segment(s) you're targeting. What
HelioGrid's four outcome KPIs *do* have is optimizable target bands
(a profit range, a market-share range, ...) that a run either lands in
or doesn't — exactly the shape `benchmark_scorecard` already models
(good/great bands per KPI, weighted into one total). So: the registry's
`benchmark_scorecard` formula does the weighted-KPI-vs-band aggregation
(see `heliogrid.json`'s `scoring_config`); this module applies the
game's own letter-grade table and the "fired" cap on top of that
formula's 0-100 total, the same way `mumbai_manufacturer_engine.py`
layers game-specific logic (there: settlement math; here: grading) on
top of a registry formula rather than forcing it all into the formula
itself.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict

from engines import scoring_registry

_GAME_PATH = os.path.join(os.path.dirname(__file__), "heliogrid.json")


def load_game() -> Dict[str, Any]:
    with open(_GAME_PATH) as f:
        return json.load(f)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def validate_action(action: Dict[str, Any], game: Dict[str, Any]) -> None:
    """Raise ValueError for a lever combination that isn't playable.

    Keeps the resolution math below free of defensive branching for
    malformed input — a route handler (or a test) calls this first.
    """
    segments = game["segments"]

    for field in ("listPrice", "headcount", "commsSpend", "researchSpend"):
        if field not in action:
            raise ValueError(f"Missing required lever '{field}'")
        if not isinstance(action[field], (int, float)) or action[field] < 0:
            raise ValueError(f"Lever '{field}' must be a non-negative number")

    discounts = action.get("discounts") or {}
    for seg in segments:
        d = discounts.get(seg, 0)
        if not isinstance(d, (int, float)) or not (0 <= d <= 20):
            raise ValueError(f"discounts['{seg}'] must be a number in [0, 20], got {d!r}")

    alloc = action.get("salesAlloc") or {}
    for seg in segments:
        if seg not in alloc:
            raise ValueError(f"salesAlloc missing segment '{seg}'")
    alloc_total = sum(alloc.get(seg, 0) for seg in segments)
    if not (99.0 <= alloc_total <= 101.0):
        raise ValueError(f"salesAlloc must sum to 100 (+/-1), got {alloc_total}")

    feature_spend = action.get("featureSpend") or {}
    for feature in ("efficiency", "mass", "latency"):
        v = feature_spend.get(feature, 0)
        if not isinstance(v, (int, float)) or v < 0:
            raise ValueError(f"featureSpend['{feature}'] must be a non-negative number")

    total_spend = (
        action.get("commsSpend", 0) + action.get("researchSpend", 0)
        + sum(feature_spend.get(f, 0) for f in ("efficiency", "mass", "latency"))
    )
    budget = game["initial_state"]["budget"]
    if total_spend > budget:
        raise ValueError(
            f"Total quarterly spend {total_spend} exceeds budget {budget}"
        )


def _fit(product_or_rival: Dict[str, float], segment: Dict[str, Any], net_price: float, cfg: Dict[str, Any]) -> float:
    want = segment["want"]
    price_gap_pct = (net_price - segment["wtp"]) / segment["wtp"]
    fit = (
        100
        - cfg["fit_efficiency_weight"] * abs(product_or_rival["efficiency"] - want["efficiency"]) / cfg["fit_efficiency_scale"]
        - cfg["fit_mass_weight"] * abs(product_or_rival["mass"] - want["mass"]) / cfg["fit_mass_scale"]
        - cfg["fit_latency_weight"] * abs(product_or_rival["latency"] - want["latency"]) / cfg["fit_latency_scale"]
        - cfg["fit_price_penalty_weight"] * max(0.0, price_gap_pct)
        + cfg["fit_price_discount_bonus_weight"] * max(0.0, -price_gap_pct)
    )
    lo, hi = cfg["fit_bounds"]
    return _clamp(fit, lo, hi)


def resolve_quarter(state: Dict[str, Any], action: Dict[str, Any], quarter_index: int, game: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve one quarter. `quarter_index` is 0-based (0..quarters-1).

    Returns a new state dict; does not mutate the input. Does not
    validate `action` — call `validate_action` first.
    """
    cfg = game["resolution_config"]
    segments = game["segments"]
    rotation = game["segment_focus_rotation"]

    state = json.loads(json.dumps(state))  # cheap deep copy, state is plain JSON-shaped
    product = state["product"]
    rival = state["rival"]

    fs = action.get("featureSpend") or {}
    spend_eff = fs.get("efficiency", 0)
    spend_mass = fs.get("mass", 0)
    spend_latency = fs.get("latency", 0)
    denom = cfg["feature_spend_denominator"]

    product["efficiency"] = _clamp(
        product["efficiency"] + spend_eff / denom * cfg["efficiency_gain_per_unit"]
        - spend_mass / denom * cfg["efficiency_mass_crosstalk"],
        *cfg["efficiency_bounds"],
    )
    product["mass"] = _clamp(
        product["mass"] - spend_mass / denom * cfg["mass_reduction_per_unit"]
        + spend_eff / denom * cfg["mass_efficiency_crosstalk"],
        *cfg["mass_bounds"],
    )
    product["latency"] = _clamp(
        product["latency"] - spend_latency / denom * cfg["latency_reduction_per_unit"],
        *cfg["latency_bounds"],
    )

    focus_key = rotation[quarter_index % len(rotation)]
    focus = segments[focus_key]
    drift = cfg["rival_feature_drift_pct"]
    rival["efficiency"] += (focus["want"]["efficiency"] - rival["efficiency"]) * drift
    rival["mass"] += (focus["want"]["mass"] - rival["mass"]) * drift
    rival["latency"] += (focus["want"]["latency"] - rival["latency"]) * drift
    rival["price"] += (
        cfg["rival_price_target_pct_of_wtp"] * focus["wtp"] - rival["price"]
    ) * cfg["rival_price_drift_pct"]

    list_price = action["listPrice"]
    discounts = action.get("discounts") or {}
    alloc = action.get("salesAlloc") or {}
    headcount = action["headcount"]
    comms_spend = action.get("commsSpend", 0)

    comms_factor = _clamp(
        0.7 + comms_spend / cfg["comms_factor_denominator"] * 0.3,
        *cfg["comms_factor_bounds"],
    )

    total_units = 0.0
    total_revenue = 0.0
    total_rival_units = 0.0
    fit_weighted_sum = 0.0

    for seg_key, seg in segments.items():
        discount_pct = discounts.get(seg_key, 0)
        net_price = list_price * (1 - discount_pct / 100)
        fit = _fit(product, seg, net_price, cfg)

        alloc_pct = alloc.get(seg_key, 0)
        effective_reps = headcount * (alloc_pct / 100)
        sales_intensity = _clamp(
            effective_reps / (cfg["sales_intensity_headcount_reference"] * seg["salesNeed"]), 0.0, 1.0
        )
        units = seg["size"] * (fit / 100) * (0.35 + 0.65 * sales_intensity) * comms_factor

        rival_fit = _fit(rival, seg, rival["price"], cfg)
        rival_units = (
            seg["size"] * (rival_fit / 100)
            * (0.35 + 0.65 * cfg["rival_sales_intensity"]) * cfg["rival_comms_factor"]
        )

        total_units += units
        total_revenue += units * net_price
        total_rival_units += rival_units
        fit_weighted_sum += fit * units

    # csat is a fit-weighted average (a ratio), so it's computed from the
    # unscaled totals before quarterly_capture_rate is applied — scaling
    # numerator and denominator by the same factor wouldn't change it, but
    # doing it before keeps that invariant obvious rather than relying on
    # cancellation.
    quarter_csat = fit_weighted_sum / total_units if total_units > 0 else 50.0

    capture_rate = cfg.get("quarterly_capture_rate", 1.0)
    total_units *= capture_rate
    total_revenue *= capture_rate
    total_rival_units *= capture_rate

    market_share_pct = (
        100.0 * total_units / (total_units + total_rival_units)
        if (total_units + total_rival_units) > 0 else 0.0
    )

    cogs_per_unit = list_price * cfg["cogs_price_fraction"] + (99 - product["efficiency"]) * cfg["cogs_efficiency_slope"]
    cogs = cogs_per_unit * total_units
    opex = comms_spend + action.get("researchSpend", 0) + spend_eff + spend_mass + spend_latency + headcount * cfg["salary_per_head"]
    profit = total_revenue - cogs - opex

    state["listPrice"] = list_price
    state["headcount"] = headcount
    state["cumulative_profit"] = state.get("cumulative_profit", 0) + profit
    state["cumulative_revenue"] = state.get("cumulative_revenue", 0) + total_revenue
    state["csat_history"] = state.get("csat_history", []) + [quarter_csat]
    state["market_share_pct"] = market_share_pct

    if profit < 0:
        state["consecutive_loss_quarters"] = state.get("consecutive_loss_quarters", 0) + 1
    else:
        state["consecutive_loss_quarters"] = 0

    state["_last_quarter_result"] = {
        "quarter_index": quarter_index,
        "focus_segment": focus_key,
        "units_sold": round(total_units, 1),
        "revenue": round(total_revenue, 2),
        "profit": round(profit, 2),
        "market_share_pct": round(market_share_pct, 2),
        "csat": round(quarter_csat, 2),
    }
    return state


def play_full_game(game: Dict[str, Any], quarter_actions: list) -> Dict[str, Any]:
    """Play every quarter in order. `quarter_actions` must have exactly
    `game['quarters']` entries. Validates each action before resolving it.
    """
    if len(quarter_actions) != game["quarters"]:
        raise ValueError(f"Expected {game['quarters']} quarter actions, got {len(quarter_actions)}")
    state = json.loads(json.dumps(game["initial_state"]))
    for i, action in enumerate(quarter_actions):
        validate_action(action, game)
        state = resolve_quarter(state, action, i, game)
    return state


def is_fired(state: Dict[str, Any], game: Dict[str, Any]) -> bool:
    threshold = game["resolution_config"]["consecutive_loss_quarters_to_fire"]
    return state.get("consecutive_loss_quarters", 0) >= threshold


def score_run(final_state: Dict[str, Any], game: Dict[str, Any]) -> scoring_registry.ScoringResult:
    cfg = game["scoring_config"]
    csat_history = final_state.get("csat_history") or []
    avg_csat = sum(csat_history) / len(csat_history) if csat_history else 50.0

    kpis = {
        "cumulative_profit": final_state.get("cumulative_profit", 0),
        "market_share_pct": final_state.get("market_share_pct", 0),
        "csat": avg_csat,
        "cumulative_revenue": final_state.get("cumulative_revenue", 0),
    }
    result = scoring_registry.compute(
        cfg["formula"],
        {"state": kpis},
        {"weights": cfg["weights"], "business_model": cfg["business_model"], "benchmarks": cfg["benchmarks"]},
    )

    total = result.total
    fired = is_fired(final_state, game)
    if fired:
        total = min(total, cfg["fired_score_cap"])
        grade, label = "F", cfg["fired_label"]
    else:
        grade, label = _lookup_grade(total, cfg["grade_table"])

    return scoring_registry.ScoringResult(
        total=round(total, 2), band=grade, label=label,
        dimensions=result.dimensions,
        raw={**result.raw, "fired": fired, "avg_csat": round(avg_csat, 2)},
    )


def _lookup_grade(total: float, grade_table: list) -> tuple:
    rows = sorted(grade_table, key=lambda r: r.get("min", 0), reverse=True)
    for row in rows:
        if total >= row.get("min", 0):
            return row.get("grade", "N/A"), row.get("label", row.get("grade", "N/A"))
    return "N/A", "N/A"
