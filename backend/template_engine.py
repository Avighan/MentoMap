"""TemplateEngine — procedural round generation from a template + seeded RNG.

app.py calls `TemplateEngine.generate_round(template, context, rng)` as a bare
class method — grepping the codebase shows no `TemplateEngine(...)` instantiation
anywhere, only this one classmethod call — so `generate_round` is implemented as
a `@staticmethod` rather than requiring an instance.

The result is dropped straight into `jsonify({"round": generated_round})`, so it
is shaped like the round objects the rest of app.py already sends the client
(`round_payload` in the run-start response: title/story/goal text plus a
`choices` list of `{id, label, delta, feedback}`).

`context` is built by app.py as `{"round_num", "day_num", **state.__dict__}`, i.e.
a flat dict of every current resource — so template text uses `{resource_name}`
placeholders resolved against it. No committed game JSON exercises `procedural`
templates yet, so the rest of the schema (variable pools, randomised delta
ranges) is inferred from what a procedural round generator needs `rng` for.

Template shape:
{
  "id": "template_id",
  "title": "...{placeholder}...",  "story": "...", "goal": "...", "image_prompt": "...",
  "variable_pools": {"name": ["a", "b", ...]},   # one rng.choice() per pool, merged into context
  "choices": [
    {"id", "label", "feedback",
     "delta": {resource: value}                    # fixed, or
     "delta_range": {resource: [min, max]}}         # rolled once per generation via rng.randint
  ]
}
"""
from typing import Any, Dict


class _SafeDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def _resolve(text: Any, context: Dict[str, Any]) -> Any:
    if not isinstance(text, str):
        return text
    try:
        return text.format_map(_SafeDict(context))
    except (KeyError, ValueError, IndexError):
        return text


class TemplateEngine:
    @staticmethod
    def generate_round(template: Dict[str, Any], context: Dict[str, Any], rng) -> Dict[str, Any]:
        ctx = dict(context or {})
        for name, pool in (template.get("variable_pools") or {}).items():
            if pool:
                ctx[name] = rng.choice(pool)

        round_data = {
            "id": template.get("id"),
            "title": _resolve(template.get("title", ""), ctx),
            "story": _resolve(template.get("story", ""), ctx),
            "goal": _resolve(template.get("goal", ""), ctx),
            "image_prompt": _resolve(template.get("image_prompt", ""), ctx),
        }

        choices = []
        for choice in template.get("choices", []) or []:
            resolved = dict(choice)
            resolved["label"] = _resolve(choice.get("label", ""), ctx)
            if "feedback" in choice:
                resolved["feedback"] = _resolve(choice.get("feedback", ""), ctx)
            delta_range = resolved.pop("delta_range", None)
            if delta_range:
                delta = dict(resolved.get("delta") or {})
                for resource, bounds in delta_range.items():
                    if isinstance(bounds, (list, tuple)) and len(bounds) == 2:
                        lo, hi = bounds
                    else:
                        lo = hi = bounds
                    delta[resource] = rng.randint(int(lo), int(hi))
                resolved["delta"] = delta
            choices.append(resolved)
        round_data["choices"] = choices
        return round_data
