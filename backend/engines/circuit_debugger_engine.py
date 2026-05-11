"""
CircuitDebuggerEngine — `circuit_debugger` repair-the-circuit game.

A simple node-voltage validator. The JSON config declares a target
node-voltage map after the circuit is "fixed". The student edits a
client-side schematic; on submit the renderer POSTs its computed node
voltages and the engine grades node-by-node against the target with a
per-node tolerance. Score = fraction of nodes within tolerance × 100.

Default dimensions: deductive_reasoning (tracing the fault) +
attention_to_detail (component values).
"""
from typing import Any, Dict, List

from engines._grader_common import coerce_weights, distribute_dimension_scores

_DEFAULT_DIMENSION_WEIGHTS = {
    "deductive_reasoning": 0.6,
    "attention_to_detail": 0.4,
}


class CircuitDebuggerEngine:
    def __init__(self, game_config: Dict[str, Any]):
        self.game_config = game_config or {}
        self.circuit = self.game_config.get("circuit") or {}
        self.weights = coerce_weights(
            self.game_config.get("dimension_scoring_weights"),
            _DEFAULT_DIMENSION_WEIGHTS,
        )

    def grade_results(self, node_voltages: Dict[str, float]) -> Dict[str, Any]:
        target = self.circuit.get("target_node_voltages") or {}
        tolerance = float((self.circuit.get("scoring") or {}).get("tolerance_v") or 0.1)

        if not target:
            return {
                "score": 0,
                "nodes_correct": 0,
                "nodes_total": 0,
                "node_results": [],
                "dimension_scores": {dim: 0 for dim in self.weights},
            }

        results: List[Dict[str, Any]] = []
        correct = 0
        for node, target_v in target.items():
            try:
                target_v = float(target_v)
                actual_v = float((node_voltages or {}).get(node, 0))
            except (TypeError, ValueError):
                actual_v = 0.0
            diff = abs(actual_v - target_v)
            ok = diff <= tolerance
            if ok:
                correct += 1
            results.append({
                "node": node,
                "target_v": round(target_v, 3),
                "actual_v": round(actual_v, 3),
                "correct": ok,
            })

        total = len(target)
        score = int(round((correct / total) * 100)) if total else 0
        return {
            "score": score,
            "nodes_correct": correct,
            "nodes_total": total,
            "node_results": results,
            "tolerance_v": tolerance,
            "dimension_scores": distribute_dimension_scores(score, self.weights),
        }
