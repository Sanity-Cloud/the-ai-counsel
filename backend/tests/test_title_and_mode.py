"""Tests for derive_conversation_title and update_conversation_mode."""

import tempfile
import pytest


@pytest.fixture
def temp_data_dir(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        from backend import config, storage
        monkeypatch.setattr(config, "DATA_DIR", tmpdir)
        monkeypatch.setattr(storage, "DATA_DIR", tmpdir)
        # Clear any cached index path
        if hasattr(storage, "_INDEX_PATH"):
            monkeypatch.setattr(storage, "_INDEX_PATH", None)
        yield tmpdir


def test_derive_title_short_text():
    from backend.council import derive_conversation_title
    assert derive_conversation_title("What is 2+2?") == "What is 2+2?"


def test_derive_title_strips_quotes_and_collapses_whitespace():
    from backend.council import derive_conversation_title
    assert derive_conversation_title('  "hello   world"  ') == "hello world"


def test_derive_title_truncates_long_text():
    from backend.council import derive_conversation_title
    long = "a " * 40
    out = derive_conversation_title(long.strip())
    assert len(out) <= 50
    assert out.endswith("...")


def test_derive_title_empty_falls_back():
    from backend.council import derive_conversation_title
    assert derive_conversation_title("") == "Untitled Conversation"
    assert derive_conversation_title("   ") == "Untitled Conversation"
    assert derive_conversation_title(None) == "Untitled Conversation"


def test_update_conversation_mode(temp_data_dir):
    from backend import storage
    conv = storage.create_conversation("conv-1", mode="council")
    storage.update_conversation_mode(conv["id"], "advisors")
    fetched = storage.get_conversation(conv["id"])
    assert fetched["mode"] == "advisors"


def test_add_user_message_does_not_touch_mode(temp_data_dir):
    from backend import storage
    conv = storage.create_conversation("conv-2", mode="council")
    storage.add_user_message(conv["id"], "Hello world")
    fetched = storage.get_conversation(conv["id"])
    assert fetched["mode"] == "council"
    assert fetched["title"] == "New Conversation"


def test_update_conversation_mode_missing_raises(temp_data_dir):
    from backend import storage
    with pytest.raises(ValueError):
        storage.update_conversation_mode("does-not-exist", "advisors")
