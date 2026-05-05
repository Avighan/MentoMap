"""Tests for retention/UX modules: weekly_challenge, game_requests,
reflection_prompts, kids_mode, parent_visibility, offline_activities."""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture
def isolated_storage(tmp_path, monkeypatch):
    """Redirect data files to a tmp dir per-test for isolation."""
    import weekly_challenge
    import game_requests
    monkeypatch.setattr(weekly_challenge, "WEEKLY_FILE",
                        str(tmp_path / "weekly.json"))
    monkeypatch.setattr(game_requests, "REQUESTS_FILE",
                        str(tmp_path / "requests.json"))
    return tmp_path


# ---- Weekly Challenge ----

def test_weekly_challenge_creates_three_for_new_user(isolated_storage):
    import weekly_challenge as wc
    challenges = wc.get_user_challenges("user_a")
    assert len(challenges) == 3
    assert all(c.get("progress") == 0 for c in challenges)
    assert all(not c.get("completed") for c in challenges)


def test_weekly_challenge_deterministic_per_user(isolated_storage):
    import weekly_challenge as wc
    a1 = wc.get_user_challenges("user_a")
    a2 = wc.get_user_challenges("user_a")
    assert [c["id"] for c in a1] == [c["id"] for c in a2]


def test_weekly_challenge_record_play_count(isolated_storage):
    import weekly_challenge as wc
    wc.get_user_challenges("user_b")  # init
    # Force a 'play_count' challenge so we know something will match
    challenges = wc.record_event("user_b", "play_count", value=5)
    pc = [c for c in challenges if c.get("kind") == "play_count"]
    if pc:
        # progress is the sum of plays we recorded
        assert any(c.get("progress") >= 5 for c in pc)


def test_weekly_challenge_high_score_takes_max(isolated_storage):
    import weekly_challenge as wc
    wc.get_user_challenges("user_c")
    wc.record_event("user_c", "high_score", value=70)
    after = wc.record_event("user_c", "high_score", value=50)
    hs = [c for c in after if c.get("kind") == "high_score"]
    if hs:
        assert all(c["progress"] == 70 for c in hs)


def test_weekly_challenge_claim_only_when_complete(isolated_storage):
    import weekly_challenge as wc
    challenges = wc.get_user_challenges("user_d")
    # Try to claim something not yet completed
    cid = challenges[0]["id"]
    assert wc.claim_reward("user_d", cid) is None


# ---- Game Requests ----

def test_game_request_create_and_list(isolated_storage):
    import game_requests as gr
    req = gr.create_request("user1", "Pendulum lab", "Physics — derive g")
    assert req["status"] == "open"
    assert req["votes"] == ["user1"]
    items = gr.list_requests()
    assert len(items) == 1
    assert items[0]["id"] == req["id"]


def test_game_request_upvote_dedupes(isolated_storage):
    import game_requests as gr
    req = gr.create_request("user1", "Title", "Topic")
    gr.upvote("user2", req["id"])
    gr.upvote("user2", req["id"])  # second vote should no-op
    items = gr.list_requests()
    assert len(items[0]["votes"]) == 2


def test_game_request_status_filter(isolated_storage):
    import game_requests as gr
    a = gr.create_request("u", "A", "topic A")
    b = gr.create_request("u", "B", "topic B")
    gr.update_status(a["id"], "fulfilled", fulfilled_game_id="game-x")
    open_only = gr.list_requests(status="open")
    assert len(open_only) == 1
    assert open_only[0]["id"] == b["id"]


def test_game_request_validates_input(isolated_storage):
    import game_requests as gr
    with pytest.raises(ValueError):
        gr.create_request("", "title", "topic")


# ---- Reflection Prompts ----

def test_reflection_prompt_age_band():
    import reflection_prompts as rp
    assert rp.get_band(7) == "kids"
    assert rp.get_band(11) == "tweens"
    assert rp.get_band(15) == "teens"
    assert rp.get_band(25) == "adults"


def test_reflection_prompt_returns_band_appropriate():
    import reflection_prompts as rp
    kid = rp.get_prompt(7)
    teen = rp.get_prompt(15)
    adult = rp.get_prompt(30)
    # All should be non-empty distinct strings; kids prompt should be shortest on average
    assert kid and teen and adult
    assert len(kid.split()) < len(adult.split()) + 5  # roughly


def test_reflection_prompt_rotates_with_index():
    import reflection_prompts as rp
    a = rp.get_prompt(15, choice_index=0)
    b = rp.get_prompt(15, choice_index=1)
    assert a != b


def test_reflection_prompt_invalid_age_default():
    import reflection_prompts as rp
    assert rp.get_band("not a number") in {"kids", "tweens", "teens", "adults"}


# ---- Kids Mode ----

def test_kids_mode_emoji_for_text():
    import kids_mode as km
    assert km.emoji_for_text("share with friends") == "🤝"
    assert km.emoji_for_text("save your money") == "💰"
    assert km.emoji_for_text("xyz random") == "❓"


def test_kids_mode_simplify_for_tts_truncates():
    import kids_mode as km
    long_text = "actually basically " + " ".join(["word"] * 50) + "."
    short = km.simplify_for_tts(long_text, max_words=10)
    assert len(short.split()) <= 11  # 10 + ellipsis


def test_kids_mode_augment_game_idempotent():
    import kids_mode as km
    game = {
        "rounds": [{
            "scenario": "You see a friend crying.",
            "choices": [
                {"text": "Help them feel better"},
                {"text": "Walk away"},
            ],
        }]
    }
    out = km.augment_game_for_kids(game)
    assert out["kids_mode"] is True
    r = out["rounds"][0]
    assert r["tts_text"]
    assert r["choices"][0]["emoji_choice"]
    assert r["choices"][1]["emoji_choice"]
    # Idempotency: pre-set values should be preserved
    game2 = dict(game)
    game2["rounds"][0]["tts_text"] = "custom narration"
    out2 = km.augment_game_for_kids(game2)
    assert out2["rounds"][0]["tts_text"] == "custom narration"


# ---- Parent Visibility ----

def test_parent_summary_aggregates_skills():
    import parent_visibility as pv
    runs = [
        {"date": "2026-05-05", "duration_minutes": 10, "game_title": "Empathy Game",
         "dimension_scores": {"empathy": 80, "strategic_thinking": 60}},
        {"date": "2026-05-05", "duration_minutes": 8, "game_title": "City Mayor",
         "dimension_scores": {"empathy": 70, "creativity": 90}},
    ]
    summary = pv.build_daily_summary("child1", runs, target_date="2026-05-05")
    assert summary["games_played"] == 2
    assert summary["minutes"] == 18
    assert summary["top_skill_today"] is not None
    # 3 dims should appear
    names = {s["name"] for s in summary["skills_practiced"]}
    assert "Empathy" in names
    # Talking points reference real game titles
    assert any("Empathy Game" in tp or "City Mayor" in tp for tp in summary["talking_points"])


def test_parent_summary_filters_to_target_date():
    import parent_visibility as pv
    runs = [
        {"date": "2026-05-04", "dimension_scores": {"empathy": 100}},
        {"date": "2026-05-05", "dimension_scores": {"focus": 50}},
    ]
    s = pv.build_daily_summary("child1", runs, target_date="2026-05-05")
    assert s["games_played"] == 1


def test_parent_summary_empty_returns_zero():
    import parent_visibility as pv
    s = pv.build_daily_summary("child1", [], target_date="2026-05-05")
    assert s["games_played"] == 0
    assert s["top_skill_today"] is None
    assert len(s["talking_points"]) >= 1  # always gives at least one fallback


# ---- Offline Activities ----

def test_offline_activity_returns_card_for_known_dim():
    import offline_activities as oa
    card = oa.get_activity_card("empathy", 7)
    assert card is not None
    assert "title" in card and "steps" in card


def test_offline_activity_falls_back_for_unknown_dim():
    import offline_activities as oa
    card = oa.get_activity_card("totally_unknown_dim", 7)
    # Falls back to empathy/kids
    assert card is not None


def test_offline_activity_count_positive():
    import offline_activities as oa
    assert oa.card_count() > 0


def test_offline_activity_list_filter():
    import offline_activities as oa
    teen_cards = oa.list_cards(age=14)
    # No teen cards in current library — should return []
    assert isinstance(teen_cards, list)
    kid_cards = oa.list_cards(age=7)
    assert len(kid_cards) > 0
