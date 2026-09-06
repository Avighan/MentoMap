"""Module-completion certificate — a self-contained printable HTML page.

`generate_certificate_html(...)` is called from
routes/module_skill_report.py's `/api/modules/<module_id>/certificate`
route once `modules_engine.check_module_completion()` reports eligibility.
Returned directly as the response body (Content-Type text/html), so it's a
full standalone document, not a fragment.
"""
from datetime import datetime
from typing import List, Optional


def generate_certificate_html(
    player_name: str,
    game_title: str,
    game_theme: str = "",
    mento_score: float = 0.0,
    mento_rank: str = "",
    badges: Optional[List[str]] = None,
    run_id: str = "",
) -> str:
    badges = badges or []
    badges_html = "".join(f'<span class="badge">{b}</span>' for b in badges)
    issued = datetime.now().strftime("%B %d, %Y")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Certificate of Completion — {game_title}</title>
<style>
  body {{ font-family: Georgia, serif; background: #f4f1ea; margin: 0;
          display: flex; align-items: center; justify-content: center; min-height: 100vh; }}
  .certificate {{ background: #fffdf7; border: 12px solid #6C5CE7; border-radius: 8px;
                  padding: 56px 64px; max-width: 720px; text-align: center;
                  box-shadow: 0 8px 30px rgba(0,0,0,0.15); }}
  .eyebrow {{ letter-spacing: 3px; text-transform: uppercase; color: #6C5CE7; font-size: 14px; }}
  h1 {{ font-size: 32px; margin: 12px 0 4px; color: #2D3047; }}
  .name {{ font-size: 40px; margin: 20px 0; color: #2D3047; border-bottom: 2px solid #FFD166;
           display: inline-block; padding-bottom: 8px; }}
  .theme {{ color: #6D7286; font-size: 16px; margin-bottom: 24px; }}
  .stats {{ display: flex; justify-content: center; gap: 40px; margin: 24px 0; }}
  .stat .value {{ font-size: 28px; font-weight: bold; color: #6C5CE7; }}
  .stat .label {{ font-size: 12px; text-transform: uppercase; color: #6D7286; }}
  .badge {{ display: inline-block; background: #FFD166; color: #2D3047; border-radius: 16px;
            padding: 4px 12px; margin: 4px; font-size: 13px; }}
  .footer {{ margin-top: 32px; font-size: 12px; color: #6D7286; }}
</style>
</head>
<body>
  <div class="certificate">
    <div class="eyebrow">Certificate of Completion</div>
    <h1>{game_title}</h1>
    <div class="name">{player_name}</div>
    <div class="theme">{game_theme}</div>
    <div class="stats">
      <div class="stat"><div class="value">{mento_score:.0f}</div><div class="label">Mento Score</div></div>
      <div class="stat"><div class="value">{mento_rank}</div><div class="label">Rank</div></div>
    </div>
    <div class="badges">{badges_html}</div>
    <div class="footer">Issued {issued} &middot; MentoMap &middot; Ref {run_id}</div>
  </div>
</body>
</html>"""
