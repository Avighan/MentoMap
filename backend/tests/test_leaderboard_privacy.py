from security.leaderboard_privacy import apply_k_anonymity

def test_below_threshold_returns_empty():
    rows = [{"user_id": "u1", "score": 90, "display_name": "Alice"},
            {"user_id": "u2", "score": 80, "display_name": "Bob"}]
    out = apply_k_anonymity(rows, k=5)
    assert out["suppressed"] is True
    assert out["rows"] == []
    assert "fewer than 5" in out["reason"].lower()

def test_at_threshold_returns_rows_with_pseudonyms():
    rows = [{"user_id": f"u{i}", "score": 100 - i, "display_name": f"Real{i}"} for i in range(5)]
    out = apply_k_anonymity(rows, k=5)
    assert out["suppressed"] is False
    assert len(out["rows"]) == 5
    for r in out["rows"]:
        assert "display_name" not in r
        assert r["peer_label"].startswith("Peer ")

def test_self_row_keeps_real_name():
    rows = [{"user_id": f"u{i}", "score": 100 - i, "display_name": f"Real{i}"} for i in range(5)]
    out = apply_k_anonymity(rows, k=5, viewer_user_id="u2")
    self_row = [r for r in out["rows"] if r["user_id"] == "u2"][0]
    assert self_row.get("is_self") is True
    assert self_row.get("display_name") == "Real2"
