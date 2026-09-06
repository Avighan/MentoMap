"""Real unit tests for backend/storage.py, restored on this branch."""
import os
import pytest


@pytest.fixture
def storage_mod(monkeypatch, tmp_path):
    # storage.py computes STORAGE_DIR/LEADERBOARD_DIR once at import time
    # (not per-call, unlike auth.py/wallet.py's dynamic _data_dir()), so
    # isolating a test run means monkeypatching those two attributes
    # directly rather than reload()ing the module — reload() mutates the
    # single shared module object every other test file's `import storage`
    # also sees, and once this test's tempdir is cleaned up that leaves
    # STORAGE_DIR pointing at a deleted directory for the rest of the
    # session (this really happened — see the fix commit message).
    import storage
    monkeypatch.setattr(storage, "STORAGE_DIR", str(tmp_path / "runs"))
    monkeypatch.setattr(storage, "LEADERBOARD_DIR", str(tmp_path / "leaderboards"))
    os.makedirs(storage.STORAGE_DIR, exist_ok=True)
    os.makedirs(storage.LEADERBOARD_DIR, exist_ok=True)
    storage.RUNS.clear()
    storage.RUNS_MTIME.clear()
    yield storage
    storage.RUNS.clear()
    storage.RUNS_MTIME.clear()


def test_create_run_wraps_dict_state_in_runstate(storage_mod):
    from engine import RunState
    run_id = storage_mod.create_run("dealcraft", {"cash": 100}, {"game_id": "dealcraft"})
    run = storage_mod.get_run(run_id)
    assert isinstance(run["state"], RunState)
    assert run["state"]["cash"] == 100
    assert run["state"].round_index == 0  # attribute access on the dict subclass


def test_get_run_raises_for_unknown_id(storage_mod):
    from storage_interface import SessionNotFoundError
    with pytest.raises(SessionNotFoundError):
        storage_mod.get_run("does-not-exist")


def test_update_run_persists_across_cache_invalidation(storage_mod):
    run_id = storage_mod.create_run("dealcraft", {"cash": 100}, {"game_id": "dealcraft"})
    run = storage_mod.get_run(run_id)
    run["state"]["cash"] = 250
    storage_mod.update_run(run_id, run)

    # Force a disk reload by dropping the in-memory cache directly.
    storage_mod.RUNS.pop(run_id, None)
    storage_mod.RUNS_MTIME.pop(run_id, None)

    reloaded = storage_mod.get_run(run_id)
    assert reloaded["state"]["cash"] == 250


def test_save_final_score_and_leaderboard_ranking(storage_mod):
    run_a = {"run_id": "a", "state": {"score": 90}}
    run_b = {"run_id": "b", "state": {"score": 60}}
    storage_mod.save_final_score("dealcraft", "user_a", run_a)
    storage_mod.save_final_score("dealcraft", "user_b", run_b)

    board = storage_mod.get_leaderboard("dealcraft", limit=10)
    assert board["total_entries"] == 2
    assert board["entries"][0]["user_id"] == "user_a"  # higher score ranks first

    rank = storage_mod.get_user_rank("dealcraft", "user_b")
    assert rank["found"] is True
    assert rank["rank"] == 2


def test_save_final_score_keeps_personal_best(storage_mod):
    run_low = {"run_id": "r1", "state": {"score": 40}}
    run_high = {"run_id": "r2", "state": {"score": 95}}
    storage_mod.save_final_score("dealcraft", "user_c", run_low)
    storage_mod.save_final_score("dealcraft", "user_c", run_high)
    # A worse follow-up run should NOT overwrite the personal best.
    storage_mod.save_final_score("dealcraft", "user_c", run_low)

    rank = storage_mod.get_user_rank("dealcraft", "user_c")
    assert rank["score"] == 95
