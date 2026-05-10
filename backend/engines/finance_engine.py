"""
Finance Engine — executive-tier financial subsystem for simulation games.

Activated only when game JSON declares `simulation_config.finance`. When absent,
all helpers return `None` and the existing single-resource ledger continues to
work unchanged.

Capabilities:
  - Cap table: founders, ESOP pool, priced rounds, dilution, post-money math
  - Three statements: P&L, Balance Sheet, Cash Flow Statement (accrual or cash)
  - Unit economics: CAC, LTV, payback, churn, NRR, gross margin, burn multiple, runway
  - Multi-period projections + scenario / Monte Carlo bands

All helpers are pure functions of (state, game_config) — they read state, never
mutate it. The engine appends per-period statements to `state.finance_history`
via `tick_finance()`.
"""
from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Optional, Tuple


# ────────────────────────────────────────────────────────────────────
# Schema activation
# ────────────────────────────────────────────────────────────────────

def get_finance_config(game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return the finance block, or None if the game doesn't declare one."""
    sim = (game or {}).get("simulation_config") or {}
    cfg = sim.get("finance")
    if not isinstance(cfg, dict):
        return None
    return cfg


# ────────────────────────────────────────────────────────────────────
# Cap table
# ────────────────────────────────────────────────────────────────────

def compute_cap_table(state: Any, game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Compute current cap table from authored rounds + dynamic state.

    Schema:
        finance.cap_table = {
          "founders": [{"name": "...", "shares": int}, ...],
          "esop_pool_pct": 0.10,
          "rounds": [
            {"name": "Seed", "raise": 1000000, "pre_money": 4000000,
             "lead": "Acme VC", "pro_rata": false, "anti_dilution": "broad-based"}
          ],
          "vesting_schedule": {"cliff_months": 12, "total_months": 48}
        }

    Returns:
        {
          "stakeholders": [{name, shares, pct, type, basis_cost}],
          "total_shares": int,
          "post_money_valuation": float,
          "fully_diluted_pct": dict,
          "esop_available": int,
          "rounds_closed": [...]
        }
    """
    cfg = get_finance_config(game)
    if not cfg:
        return None
    ct = cfg.get("cap_table") or {}
    founders = list(ct.get("founders") or [])
    esop_pct = float(ct.get("esop_pool_pct", 0.10))
    rounds = list(ct.get("rounds") or [])

    # State overrides allow choices to mutate the cap table at runtime
    runtime_rounds = list(getattr(state, "_finance_runtime_rounds", []) or [])
    rounds = rounds + runtime_rounds

    founder_shares = sum(int(f.get("shares", 0) or 0) for f in founders)
    if founder_shares <= 0:
        founder_shares = 8_000_000  # default founder pool

    # Initial total = founders / (1 - esop_pct) so ESOP fills its slice
    total = founder_shares / max(0.001, 1.0 - esop_pct)
    esop_shares = int(total - founder_shares)
    investors: List[Dict[str, Any]] = []

    last_post_money = 0.0
    last_share_price = 0.0
    for rnd in rounds:
        raise_amt = float(rnd.get("raise", 0) or 0)
        pre_money = float(rnd.get("pre_money", 0) or 0)
        if raise_amt <= 0 or pre_money <= 0:
            continue
        # New money buys shares at pre_money / pre_round_total
        share_price = pre_money / total
        new_shares = raise_amt / max(0.0001, share_price)
        total += new_shares
        last_post_money = pre_money + raise_amt
        last_share_price = share_price
        investors.append({
            "name": rnd.get("lead") or rnd.get("name", "Investor"),
            "round": rnd.get("name", "Round"),
            "shares": int(new_shares),
            "invested": int(raise_amt),
            "share_price": round(share_price, 4),
            "ownership_at_close": new_shares / total,
        })

    stakeholders: List[Dict[str, Any]] = []
    for f in founders:
        s = int(f.get("shares", 0) or 0)
        stakeholders.append({
            "name": f.get("name", "Founder"),
            "type": "founder",
            "shares": s,
            "pct": s / max(1, total),
        })
    stakeholders.append({
        "name": "ESOP Pool",
        "type": "esop",
        "shares": int(esop_shares),
        "pct": esop_shares / max(1, total),
    })
    for inv in investors:
        stakeholders.append({
            "name": inv["name"],
            "type": "investor",
            "shares": inv["shares"],
            "pct": inv["shares"] / max(1, total),
            "invested": inv["invested"],
            "share_price": inv["share_price"],
        })

    return {
        "stakeholders": stakeholders,
        "total_shares": int(total),
        "post_money_valuation": last_post_money or pre_money_default(cfg),
        "share_price": round(last_share_price, 4) if last_share_price else None,
        "esop_available_shares": int(esop_shares),
        "esop_pool_pct": esop_pct,
        "rounds_closed": [{
            "name": r.get("name"),
            "raise": r.get("raise"),
            "pre_money": r.get("pre_money"),
            "post_money": float(r.get("pre_money", 0) or 0) + float(r.get("raise", 0) or 0),
            "lead": r.get("lead"),
        } for r in rounds],
    }


def pre_money_default(cfg: Dict[str, Any]) -> float:
    return float((cfg.get("cap_table") or {}).get("starting_valuation", 0) or 0)


def apply_funding_round(state: Any, round_spec: Dict[str, Any]) -> None:
    """Mutate state to record a new funding round (called from choice handlers).

    `round_spec` matches the cap_table.rounds entry shape.
    """
    rounds = list(getattr(state, "_finance_runtime_rounds", []) or [])
    rounds.append(dict(round_spec))
    try:
        setattr(state, "_finance_runtime_rounds", rounds)
        # Cash inflow from raise — the engine assumes accrual books; real cash
        # is added to state.money so the existing ledger stays consistent.
        state.money = int(getattr(state, "money", 0) or 0) + int(round_spec.get("raise", 0) or 0)
    except Exception:
        pass


# ────────────────────────────────────────────────────────────────────
# Three statements: P&L, BS, CFS
# ────────────────────────────────────────────────────────────────────

def compute_pnl(state: Any, game: Dict[str, Any], period: int = 1) -> Optional[Dict[str, Any]]:
    """Compute the P&L for the latest period from state-tracked line items.

    Convention: state.finance_periods is a list of dicts authored by tick rules
    or choice effects. Each period dict can have:
        revenue, cogs, opex (dict), other_income, taxes, depreciation
    If absent, we synthesise a minimal P&L from the existing money delta so
    every game with finance enabled gets *some* statement.
    """
    cfg = get_finance_config(game)
    if not cfg:
        return None
    periods = list(getattr(state, "finance_periods", []) or [])
    if not periods:
        return _synth_pnl_from_state(state)
    p = periods[-1] if period == -1 else (periods[period - 1] if period <= len(periods) else periods[-1])
    revenue = float(p.get("revenue", 0) or 0)
    cogs = float(p.get("cogs", 0) or 0)
    opex_dict = p.get("opex", {}) or {}
    opex_total = sum(float(v or 0) for v in opex_dict.values())
    other = float(p.get("other_income", 0) or 0)
    dep = float(p.get("depreciation", 0) or 0)
    taxes = float(p.get("taxes", 0) or 0)
    gross_profit = revenue - cogs
    operating_income = gross_profit - opex_total - dep
    pre_tax = operating_income + other
    net_income = pre_tax - taxes
    return {
        "period_label": p.get("label") or f"Period {period}",
        "revenue": revenue,
        "cogs": cogs,
        "gross_profit": gross_profit,
        "gross_margin_pct": (gross_profit / revenue * 100.0) if revenue else 0.0,
        "opex_breakdown": dict(opex_dict),
        "opex_total": opex_total,
        "depreciation": dep,
        "operating_income": operating_income,
        "operating_margin_pct": (operating_income / revenue * 100.0) if revenue else 0.0,
        "other_income": other,
        "pre_tax_income": pre_tax,
        "taxes": taxes,
        "net_income": net_income,
        "net_margin_pct": (net_income / revenue * 100.0) if revenue else 0.0,
    }


def _synth_pnl_from_state(state: Any) -> Dict[str, Any]:
    """Best-effort P&L when no authored line items exist — keeps the widget
    populated for early-game rounds before financial structure is defined."""
    return {
        "period_label": "Current",
        "revenue": 0.0, "cogs": 0.0, "gross_profit": 0.0, "gross_margin_pct": 0.0,
        "opex_breakdown": {}, "opex_total": 0.0, "depreciation": 0.0,
        "operating_income": 0.0, "operating_margin_pct": 0.0,
        "other_income": 0.0, "pre_tax_income": 0.0, "taxes": 0.0,
        "net_income": 0.0, "net_margin_pct": 0.0,
        "synthetic": True,
    }


def compute_balance_sheet(state: Any, game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Compute a snapshot balance sheet from cumulative finance_periods + cap table."""
    cfg = get_finance_config(game)
    if not cfg:
        return None
    cash = int(getattr(state, "money", 0) or 0)
    periods = list(getattr(state, "finance_periods", []) or [])

    # Aggregate retained earnings from net income across periods
    retained_earnings = 0.0
    for p in periods:
        rev = float(p.get("revenue", 0) or 0)
        cogs = float(p.get("cogs", 0) or 0)
        opex = sum(float(v or 0) for v in (p.get("opex", {}) or {}).values())
        dep = float(p.get("depreciation", 0) or 0)
        other = float(p.get("other_income", 0) or 0)
        taxes = float(p.get("taxes", 0) or 0)
        retained_earnings += (rev - cogs - opex - dep + other - taxes)

    # Capital raised = sum of round raises
    cap_table = compute_cap_table(state, game) or {}
    paid_in_capital = sum(int(r.get("raise", 0) or 0) for r in cap_table.get("rounds_closed", []))

    # Receivables / inventory / fixed assets from authored state if present
    ar = float(getattr(state, "accounts_receivable", 0) or 0)
    inventory = float(getattr(state, "inventory", 0) or 0)
    fa = float(getattr(state, "fixed_assets", 0) or 0)
    accum_dep = float(getattr(state, "accumulated_depreciation", 0) or 0)
    intangibles = float(getattr(state, "intangibles", 0) or 0)
    total_assets = cash + ar + inventory + (fa - accum_dep) + intangibles

    ap = float(getattr(state, "accounts_payable", 0) or 0)
    short_debt = float(getattr(state, "short_term_debt", 0) or 0)
    long_debt = float(getattr(state, "long_term_debt", 0) or 0)
    deferred_rev = float(getattr(state, "deferred_revenue", 0) or 0)
    total_liabilities = ap + short_debt + long_debt + deferred_rev

    equity = paid_in_capital + retained_earnings
    return {
        "assets": {
            "cash": cash,
            "accounts_receivable": ar,
            "inventory": inventory,
            "net_fixed_assets": fa - accum_dep,
            "intangibles": intangibles,
            "total": total_assets,
        },
        "liabilities": {
            "accounts_payable": ap,
            "short_term_debt": short_debt,
            "long_term_debt": long_debt,
            "deferred_revenue": deferred_rev,
            "total": total_liabilities,
        },
        "equity": {
            "paid_in_capital": paid_in_capital,
            "retained_earnings": retained_earnings,
            "total": equity,
        },
        "total_liab_equity": total_liabilities + equity,
        "balanced": abs((total_liabilities + equity) - total_assets) < 1.0,
    }


def compute_cash_flow_statement(state: Any, game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Compute the latest period's cash flow statement (operating / investing / financing)."""
    cfg = get_finance_config(game)
    if not cfg:
        return None
    pnl = compute_pnl(state, game, period=-1) or {}
    periods = list(getattr(state, "finance_periods", []) or [])
    if not periods:
        return None
    p = periods[-1]
    operating = (
        pnl.get("net_income", 0)
        + pnl.get("depreciation", 0)
        - float(p.get("delta_ar", 0) or 0)
        - float(p.get("delta_inventory", 0) or 0)
        + float(p.get("delta_ap", 0) or 0)
    )
    investing = -float(p.get("capex", 0) or 0) - float(p.get("intangible_invest", 0) or 0)
    financing = (
        float(p.get("equity_raised", 0) or 0)
        + float(p.get("debt_raised", 0) or 0)
        - float(p.get("debt_repaid", 0) or 0)
        - float(p.get("dividends", 0) or 0)
    )
    return {
        "period_label": p.get("label") or "Current",
        "operating_cash_flow": operating,
        "investing_cash_flow": investing,
        "financing_cash_flow": financing,
        "net_change_in_cash": operating + investing + financing,
    }


# ────────────────────────────────────────────────────────────────────
# Unit economics
# ────────────────────────────────────────────────────────────────────

def compute_unit_economics(state: Any, game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Compute CAC, LTV, payback, churn, NRR, gross margin, burn multiple, runway.

    Inputs from state (any subset works; missing inputs → null on output):
        marketing_spend, new_customers, mrr / arr, gross_margin_pct,
        churn_pct (monthly), expansion_pct (monthly), monthly_burn,
        cash (defaults to state.money)
    """
    cfg = get_finance_config(game)
    if not cfg:
        return None
    ms = float(getattr(state, "marketing_spend", 0) or 0)
    new_cust = float(getattr(state, "new_customers", 0) or 0)
    cac = (ms / new_cust) if new_cust > 0 else None

    arpu = float(getattr(state, "arpu", 0) or 0)
    gross_margin_pct = float(getattr(state, "gross_margin_pct", 0) or 0)
    churn_pct = float(getattr(state, "churn_pct", 0) or 0)
    expansion_pct = float(getattr(state, "expansion_pct", 0) or 0)

    if arpu > 0 and churn_pct > 0:
        # LTV = ARPU * gross_margin% / churn% (monthly)
        ltv = arpu * (gross_margin_pct / 100.0) / (churn_pct / 100.0)
    else:
        ltv = None

    ltv_to_cac = (ltv / cac) if (ltv and cac) else None
    payback_months = (cac / (arpu * gross_margin_pct / 100.0)) if (cac and arpu and gross_margin_pct) else None
    nrr = (1.0 - churn_pct / 100.0 + expansion_pct / 100.0) * 100.0 if (churn_pct or expansion_pct) else None

    monthly_burn = float(getattr(state, "monthly_burn", 0) or 0)
    cash = int(getattr(state, "money", 0) or 0)
    runway_months = (cash / monthly_burn) if monthly_burn > 0 else None

    new_arr = float(getattr(state, "new_arr_added", 0) or 0)
    burn_multiple = (monthly_burn / new_arr) if (monthly_burn > 0 and new_arr > 0) else None

    return {
        "cac": cac,
        "ltv": ltv,
        "ltv_to_cac": ltv_to_cac,
        "payback_months": payback_months,
        "gross_margin_pct": gross_margin_pct or None,
        "churn_pct": churn_pct or None,
        "nrr_pct": nrr,
        "monthly_burn": monthly_burn or None,
        "runway_months": runway_months,
        "burn_multiple": burn_multiple,
        "cash_on_hand": cash,
    }


# ────────────────────────────────────────────────────────────────────
# Projections + Monte Carlo
# ────────────────────────────────────────────────────────────────────

def project_forward(
    state: Any,
    game: Dict[str, Any],
    horizon_months: int = 12,
    growth_pct: float = 0.10,
    perturb: float = 0.0,
    seed: Optional[int] = None,
) -> Optional[List[Dict[str, Any]]]:
    """Simple forward projection of cash + revenue path.

    `perturb` (0–1): per-period stddev for monte-carlo. 0 = deterministic.
    """
    cfg = get_finance_config(game)
    if not cfg:
        return None
    rng = random.Random(seed)
    cash = float(getattr(state, "money", 0) or 0)
    revenue = float(getattr(state, "monthly_revenue", 0) or 0)
    burn = float(getattr(state, "monthly_burn", 0) or 0)
    path = []
    for m in range(1, horizon_months + 1):
        g = growth_pct + (rng.gauss(0, perturb) if perturb else 0)
        revenue = max(0.0, revenue * (1.0 + g / 12.0))
        burn = max(0.0, burn * (1.0 + (perturb / 4.0) * (rng.gauss(0, 1) if perturb else 0)))
        cash += revenue - burn
        path.append({"month": m, "cash": round(cash, 0), "revenue": round(revenue, 0), "burn": round(burn, 0)})
    return path


def monte_carlo_bands(
    state: Any,
    game: Dict[str, Any],
    horizon_months: int = 12,
    n_sims: int = 200,
    growth_pct: float = 0.10,
    perturb: float = 0.20,
) -> Optional[Dict[str, Any]]:
    """Run N simulations and return P10/P50/P90 cash + revenue paths."""
    if get_finance_config(game) is None:
        return None
    paths = []
    for i in range(n_sims):
        p = project_forward(state, game, horizon_months, growth_pct, perturb, seed=i)
        if p:
            paths.append(p)
    if not paths:
        return None

    def _percentile(values: List[float], pct: float) -> float:
        s = sorted(values)
        if not s:
            return 0.0
        k = (len(s) - 1) * pct
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return s[int(k)]
        return s[f] + (s[c] - s[f]) * (k - f)

    bands = []
    for m in range(horizon_months):
        cashes = [p[m]["cash"] for p in paths]
        revs = [p[m]["revenue"] for p in paths]
        bands.append({
            "month": m + 1,
            "cash_p10": _percentile(cashes, 0.10),
            "cash_p50": _percentile(cashes, 0.50),
            "cash_p90": _percentile(cashes, 0.90),
            "revenue_p10": _percentile(revs, 0.10),
            "revenue_p50": _percentile(revs, 0.50),
            "revenue_p90": _percentile(revs, 0.90),
        })
    return {"horizon_months": horizon_months, "n_sims": n_sims, "bands": bands}


# ────────────────────────────────────────────────────────────────────
# Tick — append a period snapshot to state.finance_history
# ────────────────────────────────────────────────────────────────────

def tick_finance(state: Any, game: Dict[str, Any], period_label: Optional[str] = None) -> None:
    """Append a finance snapshot to state.finance_history. Idempotent per label."""
    if not get_finance_config(game):
        return
    history = list(getattr(state, "finance_history", []) or [])
    snapshot = {
        "label": period_label or f"Period {len(history) + 1}",
        "pnl": compute_pnl(state, game, period=-1),
        "balance_sheet": compute_balance_sheet(state, game),
        "cash_flow": compute_cash_flow_statement(state, game),
        "unit_economics": compute_unit_economics(state, game),
        "cap_table_summary": _cap_table_summary(state, game),
    }
    history.append(snapshot)
    try:
        setattr(state, "finance_history", history[-24:])  # cap at 24 periods
    except Exception:
        pass


def roll_forward_period(
    state: Any,
    game: Dict[str, Any],
    period_label: Optional[str] = None,
    period_inputs: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Close the current finance period and roll cash forward to the next.

    HBR-parity sims advance in coarse-grained periods (week / quarter). At each
    period boundary we:
      1. Append a new entry to `state.finance_periods` from `period_inputs`
         (revenue, cogs, opex, etc.). If `period_inputs` is None, we synthesise
         a zero entry — the period still rolls, just with no recognised activity.
      2. Take a finance_history snapshot via `tick_finance` so the period close
         is queryable for replay/scoring.
      3. Return the cash_carry_forward (= current state.money) so caller can
         set it as opening cash on the next period.

    Returns None when finance isn't configured. Does not mutate `game`.
    """
    cfg = get_finance_config(game)
    if not cfg:
        return None

    periods = list(getattr(state, "finance_periods", []) or [])
    period_index = len(periods) + 1
    label = period_label or f"Period {period_index}"

    inputs = dict(period_inputs or {})
    new_entry: Dict[str, Any] = {
        "label": label,
        "revenue": float(inputs.get("revenue", 0) or 0),
        "cogs": float(inputs.get("cogs", 0) or 0),
        "opex": dict(inputs.get("opex") or {}),
        "other_income": float(inputs.get("other_income", 0) or 0),
        "depreciation": float(inputs.get("depreciation", 0) or 0),
        "taxes": float(inputs.get("taxes", 0) or 0),
        "delta_ar": float(inputs.get("delta_ar", 0) or 0),
        "delta_inventory": float(inputs.get("delta_inventory", 0) or 0),
        "delta_ap": float(inputs.get("delta_ap", 0) or 0),
        "capex": float(inputs.get("capex", 0) or 0),
        "intangible_invest": float(inputs.get("intangible_invest", 0) or 0),
        "equity_raised": float(inputs.get("equity_raised", 0) or 0),
        "debt_raised": float(inputs.get("debt_raised", 0) or 0),
        "debt_repaid": float(inputs.get("debt_repaid", 0) or 0),
        "dividends": float(inputs.get("dividends", 0) or 0),
    }
    periods.append(new_entry)
    try:
        setattr(state, "finance_periods", periods)
    except Exception:
        pass

    # Snapshot for replay
    try:
        tick_finance(state, game, period_label=label)
    except Exception:
        pass

    cash_carry = int(getattr(state, "money", 0) or 0)
    return {
        "period_label": label,
        "period_index": period_index,
        "cash_carry_forward": cash_carry,
    }


def _cap_table_summary(state: Any, game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    ct = compute_cap_table(state, game)
    if not ct:
        return None
    return {
        "post_money_valuation": ct.get("post_money_valuation"),
        "rounds_count": len(ct.get("rounds_closed", [])),
        "founder_dilution_pct": sum(
            s["pct"] for s in ct.get("stakeholders", []) if s.get("type") == "founder"
        ),
    }


# ────────────────────────────────────────────────────────────────────
# Public payload builder — called from build_ux_payload
# ────────────────────────────────────────────────────────────────────

def build_finance_payload(state: Any, game: Dict[str, Any]) -> Dict[str, Any]:
    """One-shot builder used by the UX enrichment layer. Always returns a dict;
    individual keys are None when finance isn't configured or computation fails."""
    payload = {
        "cap_table": None,
        "pnl": None,
        "balance_sheet": None,
        "cash_flow": None,
        "unit_economics": None,
        "projections": None,
    }
    if not get_finance_config(game):
        return payload
    try:
        payload["cap_table"] = compute_cap_table(state, game)
    except Exception:
        pass
    try:
        payload["pnl"] = compute_pnl(state, game, period=-1)
    except Exception:
        pass
    try:
        payload["balance_sheet"] = compute_balance_sheet(state, game)
    except Exception:
        pass
    try:
        payload["cash_flow"] = compute_cash_flow_statement(state, game)
    except Exception:
        pass
    try:
        payload["unit_economics"] = compute_unit_economics(state, game)
    except Exception:
        pass
    try:
        cfg = get_finance_config(game) or {}
        proj_cfg = cfg.get("projections") or {}
        if proj_cfg.get("enabled"):
            horizon = int(proj_cfg.get("horizon_months", 12))
            growth = float(proj_cfg.get("growth_pct", 0.10))
            if proj_cfg.get("monte_carlo"):
                payload["projections"] = monte_carlo_bands(
                    state, game,
                    horizon_months=horizon,
                    n_sims=int(proj_cfg.get("n_sims", 200)),
                    growth_pct=growth,
                    perturb=float(proj_cfg.get("perturb", 0.20)),
                )
            else:
                payload["projections"] = {
                    "horizon_months": horizon,
                    "deterministic": project_forward(state, game, horizon, growth),
                }
    except Exception:
        pass
    return payload
