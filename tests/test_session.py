import ai.session as session_mod
from ai.session import Session, get_or_create, lock_for, mirror, reset


def test_get_or_create_returns_same_instance():
    s1 = get_or_create("t-same")
    s1.name = "Aman"
    s2 = get_or_create("t-same")
    assert s1 is s2
    assert s2.name == "Aman"


def test_sessions_are_isolated_by_id():
    a = get_or_create("t-iso-A")
    b = get_or_create("t-iso-B")
    a.add("user", "A's message")
    b.add("user", "B's message")
    assert a.history == [{"role": "user", "content": "A's message"}]
    assert b.history == [{"role": "user", "content": "B's message"}]


def test_add_appends_with_extra_fields():
    s = Session(id="t-add")
    s.add("user", "hi")
    s.add("assistant", None, tool_calls=[{"id": "x"}])
    assert s.history[0] == {"role": "user", "content": "hi"}
    # content omitted when None; extras preserved
    assert s.history[1] == {"role": "assistant", "tool_calls": [{"id": "x"}]}


def test_reset_drops_session():
    get_or_create("t-reset").name = "X"
    reset("t-reset")
    fresh = get_or_create("t-reset")
    assert fresh.name is None


def test_lock_is_stable_per_id():
    assert lock_for("t-lock") is lock_for("t-lock")
    assert lock_for("t-lock-A") is not lock_for("t-lock-B")


def test_mirror_maps_fields(monkeypatch):
    captured = {}

    def fake_upsert(session_id, **fields):
        captured["id"] = session_id
        captured["fields"] = fields
        return True

    monkeypatch.setattr(session_mod.db_sessions, "upsert_session", fake_upsert)

    s = Session(id="t-mirror", channel="voice", language="hi", status="ordered")
    s.name = "Priya"
    s.phone = "9876543210"
    assert mirror(s) is True
    assert captured["id"] == "t-mirror"
    assert captured["fields"]["customer_name"] == "Priya"
    assert captured["fields"]["customer_phone"] == "9876543210"
    assert captured["fields"]["channel"] == "voice"
    assert captured["fields"]["language"] == "hi"
    assert captured["fields"]["status"] == "ordered"
