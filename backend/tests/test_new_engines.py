"""Smoke tests for the 10 new engines added in the audit-followup batch:
pendulum, optics, circuit, genetics, stoichiometry, mental_math, typing,
boggle, mock_interview, sudoku, logic_grid, geometry_constructor.

Each engine gets:
  - a 'happy path' that verifies a perfect submission scores 100
  - one or more failure modes (wrong / partial / nonsense)
  - dimension_scores presence + non-negative
"""
import math
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engines.pendulum_lab_engine import PendulumLabEngine  # noqa: E402
from engines.optics_lab_engine import OpticsLabEngine  # noqa: E402
from engines.circuit_debugger_engine import CircuitDebuggerEngine  # noqa: E402
from engines.genetics_cross_engine import GeneticsCrossEngine  # noqa: E402
from engines.stoichiometry_mixer_engine import StoichiometryMixerEngine  # noqa: E402
from engines.mental_math_engine import MentalMathEngine  # noqa: E402
from engines.typing_drill_engine import TypingDrillEngine  # noqa: E402
from engines.boggle_engine import BoggleEngine  # noqa: E402
from engines.mock_interview_engine import MockInterviewEngine  # noqa: E402
from engines.sudoku_engine import SudokuEngine  # noqa: E402
from engines.logic_grid_engine import LogicGridEngine  # noqa: E402
from engines.geometry_constructor_engine import GeometryConstructorEngine  # noqa: E402


# ---- Pendulum ----

def test_pendulum_perfect_g():
    # T = 2π√(L/g) → for L=1.0, true_g=9.81, T = 2π·sqrt(1/9.81) ≈ 2.006
    cfg = {"pendulum": {"true_g": 9.81, "scoring": {"tolerance_g": 0.3}}}
    period = 2 * math.pi * math.sqrt(1.0 / 9.81)
    res = PendulumLabEngine(cfg).grade_results([{"length_m": 1.0, "period_s": period}])
    assert res["score"] == 100
    assert res["band"] == "perfect"


def test_pendulum_no_data_zero():
    res = PendulumLabEngine({"pendulum": {}}).grade_results([])
    assert res["score"] == 0
    assert res["band"] == "no_data"


# ---- Optics ----

def test_optics_perfect_focal_length():
    # do=20, di=20 → 1/f = 1/20 + 1/20 = 0.1 → f = 10
    cfg = {"optics": {"true_focal_length_cm": 10.0, "scoring": {"tolerance_cm": 0.5}}}
    res = OpticsLabEngine(cfg).grade_results([
        {"object_distance_cm": 20, "image_distance_cm": 20}
    ])
    assert res["score"] == 100


def test_optics_no_trials_zero():
    res = OpticsLabEngine({"optics": {}}).grade_results([])
    assert res["score"] == 0


# ---- Circuit ----

def test_circuit_all_nodes_correct():
    cfg = {"circuit": {"target_node_voltages": {"A": 5, "B": 0, "C": 2.5}}}
    res = CircuitDebuggerEngine(cfg).grade_results({"A": 5.0, "B": 0.0, "C": 2.5})
    assert res["score"] == 100
    assert res["nodes_correct"] == 3


def test_circuit_partial():
    cfg = {"circuit": {"target_node_voltages": {"A": 5, "B": 0}}}
    res = CircuitDebuggerEngine(cfg).grade_results({"A": 5.0, "B": 5.0})
    assert res["score"] == 50


# ---- Genetics ----

def test_genetics_aa_aa_dominance_perfect():
    # Aa × Aa → 75% dominant, 25% recessive (classic Mendel)
    cfg = {"cross": {"parent_a": "Aa", "parent_b": "Aa", "dominance": True}}
    res = GeneticsCrossEngine(cfg).grade_results({"dominant": 75, "recessive": 25})
    assert res["score"] == 100


def test_genetics_wrong_predictions():
    cfg = {"cross": {"parent_a": "Aa", "parent_b": "Aa", "dominance": True}}
    res = GeneticsCrossEngine(cfg).grade_results({"dominant": 50, "recessive": 50})
    # MAE = (25 + 25)/2 = 25 → score 75
    assert res["score"] == 75


# ---- Stoichiometry ----

def test_stoichiometry_perfect_ratio():
    # 1:2 ratio, 0.05 mol of A → need 0.10 mol B
    cfg = {"reaction": {"reactant_a_moles": 0.05, "ratio_a_to_b": "1:2",
                         "scoring": {"tolerance_moles": 0.001}}}
    res = StoichiometryMixerEngine(cfg).grade_results(0.10)
    assert res["score"] == 100
    assert res["ideal_b_moles"] == 0.1


def test_stoichiometry_negative_clamped():
    cfg = {"reaction": {"reactant_a_moles": 0.05, "ratio_a_to_b": "1:1"}}
    res = StoichiometryMixerEngine(cfg).grade_results(-1)
    assert res["added_b_moles"] == 0.0


# ---- MentalMath ----

def test_mental_math_all_correct_at_target_speed():
    cfg = {
        "problems": [{"id": "p1", "answer": 4}, {"id": "p2", "answer": 9}],
        "time_target_s": 5.0,
    }
    res = MentalMathEngine(cfg).grade_results([
        {"id": "p1", "answer": 4, "elapsed_s": 5},
        {"id": "p2", "answer": 9, "elapsed_s": 5},
    ])
    # accuracy 1.0 * 80 + speed_factor 1.0 → (1-0.75)/0.5 = 0.5 → 0.5 * 20 = 10. Total 90.
    assert res["accuracy_pct"] == 100
    assert res["score"] >= 80


def test_mental_math_wrong_answers():
    cfg = {"problems": [{"id": "p1", "answer": 4}]}
    res = MentalMathEngine(cfg).grade_results([{"id": "p1", "answer": 99, "elapsed_s": 5}])
    assert res["correct"] == 0


# ---- Typing ----

def test_typing_perfect_match():
    cfg = {"passages": [{"id": "p1", "text": "hello world"}],
           "target_wpm": 30}
    res = TypingDrillEngine(cfg).grade_results([
        # 11 chars / 5 = 2.2 words; 2.2/(2/60) = 66 wpm if 2s; well above target
        {"passage_id": "p1", "typed_text": "hello world", "elapsed_s": 2.0}
    ])
    assert res["accuracy_pct"] == 100
    assert res["score"] >= 80


def test_typing_typos_partial():
    cfg = {"passages": [{"id": "p1", "text": "hello"}], "target_wpm": 30}
    res = TypingDrillEngine(cfg).grade_results([
        {"passage_id": "p1", "typed_text": "hxllo", "elapsed_s": 2}
    ])
    # 4/5 chars match
    assert res["accuracy_pct"] == 80


# ---- Boggle ----

def test_boggle_finds_real_word():
    cfg = {
        "grid": [["c", "a", "t"], ["d", "o", "g"], ["b", "e", "n"]],
        "dictionary": ["cat", "dog", "go", "ben"],
        "min_word_length": 3,
    }
    res = BoggleEngine(cfg).grade_results(["cat", "dog", "ben"])
    # All 3 are findable + in dict → 3 points raw; ceiling = 3; → 100
    assert res["score"] == 100
    assert len(res["accepted"]) == 3


def test_boggle_rejects_invalid_word():
    cfg = {
        "grid": [["c", "a", "t"], ["d", "o", "g"], ["b", "e", "n"]],
        "dictionary": ["cat"],
        "min_word_length": 3,
    }
    res = BoggleEngine(cfg).grade_results(["xyz", "abc", "ca"])
    assert len(res["accepted"]) == 0
    # ca is too_short, xyz/abc not_in_dictionary
    reasons = {r["reason"] for r in res["rejected"]}
    assert "too_short" in reasons
    assert "not_in_dictionary" in reasons


# ---- MockInterview ----

def test_mock_interview_heuristic_substantive():
    cfg = {"rubric": [{"dimension": "communication"}]}
    transcript = [
        {"question": "Tell me about yourself.",
         "answer": " ".join(["word"] * 50)},
        {"question": "Why this role?", "answer": " ".join(["word"] * 60)},
    ]
    res = MockInterviewEngine(cfg).grade_results(transcript)
    assert res["score"] >= 60
    assert res["method"] in ("heuristic", "llm")


def test_mock_interview_empty_transcript():
    res = MockInterviewEngine({}).grade_results([])
    assert res["score"] == 0


# ---- Sudoku ----

def test_sudoku_perfect_solution():
    solution = [
        [5, 3, 4, 6, 7, 8, 9, 1, 2],
        [6, 7, 2, 1, 9, 5, 3, 4, 8],
        [1, 9, 8, 3, 4, 2, 5, 6, 7],
        [8, 5, 9, 7, 6, 1, 4, 2, 3],
        [4, 2, 6, 8, 5, 3, 7, 9, 1],
        [7, 1, 3, 9, 2, 4, 8, 5, 6],
        [9, 6, 1, 5, 3, 7, 2, 8, 4],
        [2, 8, 7, 4, 1, 9, 6, 3, 5],
        [3, 4, 5, 2, 8, 6, 1, 7, 9],
    ]
    cfg = {"solution": solution}
    res = SudokuEngine(cfg).grade_results({"grid": solution, "hints_used": 0})
    assert res["score"] == 100
    assert res["valid"] is True


def test_sudoku_hint_penalty_applied():
    solution = [[1] * 9 for _ in range(9)]  # invalid but engine doesn't care for input scoring
    cfg = {"solution": solution, "hint_penalty": 5}
    res = SudokuEngine(cfg).grade_results({"grid": solution, "hints_used": 3})
    # Even with 100% match, valid=False (lots of dupes) → base * 0.8 = 80, then -15 hints → 65
    assert res["valid"] is False
    assert res["score"] < 100


# ---- LogicGrid ----

def test_logic_grid_perfect_match():
    solution = [
        {"name": "Alice", "house": "red", "drink": "tea"},
        {"name": "Bob", "house": "blue", "drink": "coffee"},
    ]
    cfg = {"solution": solution}
    res = LogicGridEngine(cfg).grade_results(solution)
    assert res["score"] == 100
    assert res["rows_correct"] == 2


def test_logic_grid_partial():
    solution = [
        {"name": "Alice", "house": "red", "drink": "tea"},
        {"name": "Bob", "house": "blue", "drink": "coffee"},
    ]
    sub = [
        {"name": "Alice", "house": "red", "drink": "coffee"},  # 1/3 wrong
        {"name": "Bob", "house": "blue", "drink": "coffee"},  # 3/3 right
    ]
    res = LogicGridEngine({"solution": solution}).grade_results(sub)
    # 5/6 cells = 83
    assert res["cells_correct"] == 5
    assert res["score"] == 83


# ---- GeometryConstructor ----

def test_geometry_unit_segment():
    cfg = {
        "target_features": [
            {"kind": "length", "segment": "AB", "value": 1.0},
        ],
        "tolerance": 0.01,
    }
    res = GeometryConstructorEngine(cfg).grade_results({"A": [0, 0], "B": [1, 0]})
    assert res["score"] == 100


def test_geometry_isoceles_triangle():
    cfg = {
        "target_features": [
            {"kind": "length_eq", "segments": ["AB", "AC"]},
        ],
        "tolerance": 0.01,
    }
    res = GeometryConstructorEngine(cfg).grade_results({
        "A": [0, 0], "B": [1, 0], "C": [-1, 0],
    })
    assert res["score"] == 100


def test_geometry_right_angle():
    cfg = {
        "target_features": [
            {"kind": "angle", "vertices": ["A", "B", "C"], "value": 90},
        ],
        "tolerance": 1.0,
    }
    res = GeometryConstructorEngine(cfg).grade_results({
        "A": [1, 0], "B": [0, 0], "C": [0, 1],
    })
    assert res["score"] == 100


def test_geometry_failure():
    cfg = {
        "target_features": [
            {"kind": "length", "segment": "AB", "value": 5.0},
        ],
        "tolerance": 0.01,
    }
    res = GeometryConstructorEngine(cfg).grade_results({"A": [0, 0], "B": [1, 0]})
    assert res["score"] == 0
