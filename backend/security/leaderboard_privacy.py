"""K-anonymity filter for leaderboard / cohort rankings.

Rule: if fewer than k distinct users are present, suppress the entire result.
At/above k, strip display_name and replace with a stable peer pseudonym.
The viewer (when known) keeps their own real name and gets is_self=True.
"""
from typing import Iterable, Optional

def apply_k_anonymity(rows: Iterable[dict], k: int = 5,
                      viewer_user_id: Optional[str] = None) -> dict:
    rows = list(rows)
    if len({r.get("user_id") for r in rows if r.get("user_id")}) < k:
        return {"suppressed": True, "reason": f"Fewer than {k} participants — leaderboard hidden to protect privacy.", "rows": []}
    out = []
    for idx, r in enumerate(rows, start=1):
        item = {kk: vv for kk, vv in r.items() if kk != "display_name"}
        if viewer_user_id and r.get("user_id") == viewer_user_id:
            item["display_name"] = r.get("display_name")
            item["is_self"] = True
        else:
            item["peer_label"] = f"Peer {idx}"
        out.append(item)
    return {"suppressed": False, "rows": out}
