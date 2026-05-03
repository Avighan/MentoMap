"""
project_management_engine — adds project execution mechanics to exec sims.

Concepts:
  - Tasks (id, name, duration_days, dependencies, owner, status, progress_pct)
  - Critical path (longest dependency chain — slipping these slips the project)
  - Burndown (planned vs actual remaining work)
  - RAID register (Risks, Assumptions, Issues, Dependencies)
  - Resource pool (people with capacity & skill)
  - Sprint backlog (subset of tasks committed for current iteration)

Game JSON opt-in:

  simulation_config:
    project_management:
      methodology: "agile" | "waterfall" | "hybrid"
      sprint_length_days: 14
      target_end_day: 90
      tasks:
        - id: "kickoff"
          name: "Project kickoff & charter"
          duration_days: 3
          dependencies: []
          owner: "pm"
          status: "done"
          progress_pct: 100
        - id: "design"
          name: "Solution design"
          duration_days: 10
          dependencies: ["kickoff"]
          owner: "tech_lead"
      resources:
        - { id: "pm",        name: "Project Manager",  capacity_pct: 100, skill: "pm" }
        - { id: "tech_lead", name: "Tech Lead",        capacity_pct: 80,  skill: "engineering" }
      raid:
        risks:        []   # [{id, label, probability, impact, mitigation, status}]
        assumptions:  []   # [{id, label, validated}]
        issues:       []   # [{id, label, severity, owner, due, status}]
        dependencies: []   # [{id, label, on, due, status}]

Choice integration (via core/exec_effects.py):

  exec_effects:
    project_task:
      id: "design"
      progress_pct: 100              # set / update progress
      status: "done"                  # one of: not_started/in_progress/blocked/done
    project_raid:
      issues:
        add:    [{id:"i1", label:"Vendor late", severity:"high", owner:"pm", status:"open"}]
        resolve:["i0_vendor_lock"]
    project_advance_day:
      days: 7                          # advance project clock 7 days

State runtime attrs:
  state._pm_runtime: {
     "current_day": int,
     "task_overrides": {task_id: {progress_pct, status, actual_duration_days}},
     "raid_overrides": {risks/assumptions/issues/dependencies: [...]},
  }
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


# ────────────────────────────────────────────────────────────────────
# Config / state helpers
# ────────────────────────────────────────────────────────────────────

def get_pm_config(game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    sim = (game or {}).get("simulation_config") or {}
    pm = sim.get("project_management")
    if not isinstance(pm, dict): return None
    if not pm.get("tasks"): return None
    return pm


def _runtime(state: Any) -> Dict[str, Any]:
    rt = getattr(state, "_pm_runtime", None)
    if not isinstance(rt, dict):
        rt = {"current_day": 0, "task_overrides": {}, "raid_overrides": {}}
        try: setattr(state, "_pm_runtime", rt)
        except Exception: pass
    return rt


# ────────────────────────────────────────────────────────────────────
# Critical path computation
# ────────────────────────────────────────────────────────────────────

def _topo_sort(tasks: List[Dict[str, Any]]) -> List[str]:
    by_id = {t["id"]: t for t in tasks if t.get("id")}
    indeg = {tid: 0 for tid in by_id}
    for t in tasks:
        for d in (t.get("dependencies") or []):
            if d in by_id:
                indeg[t["id"]] = indeg.get(t["id"], 0) + 1
    queue = [tid for tid, d in indeg.items() if d == 0]
    out = []
    while queue:
        n = queue.pop(0)
        out.append(n)
        for t in tasks:
            if n in (t.get("dependencies") or []):
                indeg[t["id"]] -= 1
                if indeg[t["id"]] == 0:
                    queue.append(t["id"])
    return out


def _critical_path(tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Forward+backward pass over the DAG. Returns {path:[tids], duration_days}."""
    by_id = {t["id"]: t for t in tasks if t.get("id")}
    if not by_id: return {"path": [], "duration_days": 0}
    order = _topo_sort(tasks)
    earliest = {tid: 0 for tid in by_id}
    parent = {tid: None for tid in by_id}
    for tid in order:
        t = by_id[tid]
        deps = [d for d in (t.get("dependencies") or []) if d in by_id]
        if deps:
            best = max(deps, key=lambda d: earliest[d] + by_id[d].get("duration_days", 0))
            earliest[tid] = earliest[best] + by_id[best].get("duration_days", 0)
            parent[tid] = best
    # End node = max(earliest + duration)
    end = max(by_id, key=lambda tid: earliest[tid] + by_id[tid].get("duration_days", 0))
    duration = earliest[end] + by_id[end].get("duration_days", 0)
    # Walk back via parent pointers
    path: List[str] = []
    cur = end
    while cur:
        path.append(cur)
        cur = parent[cur]
    return {"path": list(reversed(path)), "duration_days": duration}


# ────────────────────────────────────────────────────────────────────
# Apply runtime overrides to base tasks
# ────────────────────────────────────────────────────────────────────

def _materialize_tasks(cfg: Dict[str, Any], state: Any) -> List[Dict[str, Any]]:
    base = list(cfg.get("tasks") or [])
    rt = _runtime(state)
    overrides = rt.get("task_overrides") or {}
    out = []
    for t in base:
        tid = t.get("id")
        merged = dict(t)
        if tid in overrides:
            merged.update(overrides[tid])
        merged.setdefault("status", "not_started")
        merged.setdefault("progress_pct", 0)
        merged.setdefault("dependencies", [])
        merged.setdefault("duration_days", 5)
        out.append(merged)
    return out


# ────────────────────────────────────────────────────────────────────
# Public payload builder (called by executive_ux)
# ────────────────────────────────────────────────────────────────────

def build_pm_payload(state: Any, game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    cfg = get_pm_config(game)
    if not cfg: return None
    tasks = _materialize_tasks(cfg, state)
    cp = _critical_path(tasks)

    # Burndown — total remaining vs target
    total_days = sum(t.get("duration_days", 0) for t in tasks)
    completed_days = sum(
        t.get("duration_days", 0) * (t.get("progress_pct", 0) / 100.0) for t in tasks
    )
    remaining_days = max(0, total_days - completed_days)

    rt = _runtime(state)
    current_day = int(rt.get("current_day", 0) or 0)
    target_end = int(cfg.get("target_end_day", cp["duration_days"]) or cp["duration_days"])
    schedule_health = "on_track"
    days_late = 0
    if target_end > 0:
        # Naive: if we've consumed > pct of target time but have less progress, we're slipping
        time_pct = current_day / max(1, target_end)
        progress_pct = completed_days / max(1, total_days)
        gap = time_pct - progress_pct
        if gap > 0.10: schedule_health = "at_risk"
        if gap > 0.20: schedule_health = "slipping"
        days_late = max(0, int(round(current_day - target_end * progress_pct)))

    # RAID
    raid_base = (cfg.get("raid") or {})
    raid_over = (rt.get("raid_overrides") or {})
    raid = {
        "risks":        list(raid_base.get("risks") or []) + list(raid_over.get("risks") or []),
        "assumptions":  list(raid_base.get("assumptions") or []) + list(raid_over.get("assumptions") or []),
        "issues":       list(raid_base.get("issues") or []) + list(raid_over.get("issues") or []),
        "dependencies": list(raid_base.get("dependencies") or []) + list(raid_over.get("dependencies") or []),
    }
    open_issues = [i for i in raid["issues"] if i.get("status") != "resolved"]
    high_risks = [r for r in raid["risks"] if r.get("status") != "closed" and (r.get("impact") in ("high", "critical"))]

    # Sprint summary (if agile)
    sprint_info = None
    if cfg.get("methodology") == "agile":
        sprint_len = int(cfg.get("sprint_length_days") or 14)
        sprint_idx = current_day // max(1, sprint_len) + 1
        sprint_info = {
            "sprint_number": sprint_idx,
            "sprint_length_days": sprint_len,
            "day_in_sprint": current_day % max(1, sprint_len),
        }

    return {
        "methodology": cfg.get("methodology", "agile"),
        "current_day": current_day,
        "target_end_day": target_end,
        "schedule_health": schedule_health,
        "days_late": days_late,
        "tasks": tasks,
        "critical_path": cp,
        "burndown": {
            "total_days":     int(total_days),
            "completed_days": round(completed_days, 1),
            "remaining_days": round(remaining_days, 1),
        },
        "raid": raid,
        "raid_summary": {
            "open_issues":  len(open_issues),
            "high_risks":   len(high_risks),
            "n_risks":      len(raid["risks"]),
            "n_assumptions":len(raid["assumptions"]),
            "n_issues":     len(raid["issues"]),
            "n_dependencies":len(raid["dependencies"]),
        },
        "sprint": sprint_info,
        "resources": cfg.get("resources") or [],
        "earned_value": compute_earned_value(state, game),
    }


# ────────────────────────────────────────────────────────────────────
# Mutation helpers (called by core/exec_effects.py)
# ────────────────────────────────────────────────────────────────────

def update_task(state: Any, task_id: str, patch: Dict[str, Any]) -> None:
    rt = _runtime(state)
    overrides = dict(rt.get("task_overrides") or {})
    cur = dict(overrides.get(task_id) or {})
    for k in ("progress_pct", "status", "actual_duration_days", "owner"):
        if k in patch: cur[k] = patch[k]
    overrides[task_id] = cur
    rt["task_overrides"] = overrides


def add_raid(state: Any, category: str, items: List[Dict[str, Any]]) -> None:
    if category not in ("risks", "assumptions", "issues", "dependencies"): return
    rt = _runtime(state)
    over = dict(rt.get("raid_overrides") or {})
    cur = list(over.get(category) or [])
    for it in items or []:
        if isinstance(it, dict) and it.get("id"):
            cur.append(it)
    over[category] = cur
    rt["raid_overrides"] = over


def resolve_raid(state: Any, category: str, ids: List[str]) -> None:
    if category not in ("risks", "assumptions", "issues", "dependencies"): return
    rt = _runtime(state)
    over = dict(rt.get("raid_overrides") or {})
    cur = list(over.get(category) or [])
    target = "closed" if category == "risks" else "resolved"
    for item in cur:
        if isinstance(item, dict) and item.get("id") in (ids or []):
            item["status"] = target
    over[category] = cur
    rt["raid_overrides"] = over


def advance_day(state: Any, days: int) -> None:
    rt = _runtime(state)
    rt["current_day"] = int(rt.get("current_day", 0) or 0) + max(0, int(days or 0))


# ────────────────────────────────────────────────────────────────────
# Earned Value Management (PV / EV / AC + variances)
# ────────────────────────────────────────────────────────────────────

def compute_earned_value(state: Any, game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Earned-value rollup: PV (planned), EV (earned), AC (actual cost) + indices.

    Per task fields used (all optional, default 0):
      - budget_cost:    BAC contribution for the task
      - actual_cost:    cost recorded against the task to date
      - progress_pct:   0–100, % complete (used for EV)
      - duration_days:  used as fallback PV weight when target_end_day not set

    Returns:
      {
        "planned_value":      PV at current_day (BAC × current_day/target_end_day),
        "earned_value":       sum(budget × progress%),
        "actual_cost":        sum(actual_cost),
        "budget_at_completion": sum(budget),
        "cost_variance":      EV - AC   (negative = over budget),
        "schedule_variance":  EV - PV   (negative = behind schedule),
        "cpi":                EV / AC   (1.0 = on budget),
        "spi":                EV / PV   (1.0 = on schedule),
        "eac":                BAC / CPI (forecast total cost),
      }
    None when project_management isn't configured.
    """
    cfg = get_pm_config(game)
    if not cfg:
        return None

    tasks = _materialize_tasks(cfg, state)
    rt = _runtime(state)
    current_day = int(rt.get("current_day", 0) or 0)
    target_end = int(cfg.get("target_end_day") or 0)

    bac = sum(float(t.get("budget_cost", 0) or 0) for t in tasks)
    ev = sum(
        float(t.get("budget_cost", 0) or 0) * (float(t.get("progress_pct", 0) or 0) / 100.0)
        for t in tasks
    )
    ac = sum(float(t.get("actual_cost", 0) or 0) for t in tasks)

    # PV = BAC × elapsed-fraction-of-schedule. Cap at BAC.
    if target_end > 0:
        pv = bac * min(1.0, max(0.0, current_day / target_end))
    else:
        # Fallback: PV proportional to (current_day / total_planned_duration)
        total_dur = sum(float(t.get("duration_days", 0) or 0) for t in tasks)
        pv = bac * min(1.0, current_day / total_dur) if total_dur > 0 else 0.0

    cv = ev - ac
    sv = ev - pv
    cpi = (ev / ac) if ac > 0 else None
    spi = (ev / pv) if pv > 0 else None
    eac = (bac / cpi) if (cpi is not None and cpi > 0) else None

    return {
        "planned_value": round(pv, 2),
        "earned_value": round(ev, 2),
        "actual_cost": round(ac, 2),
        "budget_at_completion": round(bac, 2),
        "cost_variance": round(cv, 2),
        "schedule_variance": round(sv, 2),
        "cpi": round(cpi, 4) if cpi is not None else None,
        "spi": round(spi, 4) if spi is not None else None,
        "eac": round(eac, 2) if eac is not None else None,
    }
