import os
for key in ("no_proxy", "NO_PROXY"):
    val = os.environ.get(key)
    if val:
        os.environ[key] = ",".join(p for p in val.split(",") if "::" not in p)

import pytest


class _FakeSettings:
    """Lightweight settings stand-in for cost tests that need custom_endpoint_*.}

    Tests that use this fixture should set any fields they need; the rest default
    to None / False. Mutate fields on the returned instance directly.
    """

    def __init__(self):
        self.custom_endpoint_name = None
        self.custom_endpoint_url = None
        self.openrouter_api_key = None
        self.openai_api_key = None
        self.anthropic_api_key = None
        self.google_api_key = None
        self.groq_api_key = None
        self.mistral_api_key = None
        self.deepseek_api_key = None
        self.nvidia_api_key = None
        self.opencode_api_key = None


@pytest.fixture
def fake_settings(monkeypatch):
    """Replace `backend.settings.get_settings` with a mutable stub.

    Returns the stub instance so tests can set fields before invoking the
    function under test. The substitution is reverted automatically at the
    end of the test.
    """
    from backend import settings as settings_module

    stub = _FakeSettings()
    monkeypatch.setattr(settings_module, "get_settings", lambda: stub)
    return stub


@pytest.fixture(autouse=True)
def reset_global_state(tmp_path, monkeypatch):
    """Autouse fixture to reset cached settings, environment variables, and providers between tests."""
    from backend import settings as settings_module
    import os

    # 1. Clear settings cache
    settings_module._settings_cache = None
    settings_module._settings_mtime = 0.0

    # 2. Redirect SETTINGS_FILE to a temp path for isolation
    import json
    temp_settings = tmp_path / "settings.json"
    with open(temp_settings, "w") as f:
        json.dump(settings_module.Settings().model_dump(), f)
    monkeypatch.setattr(settings_module, "SETTINGS_FILE", temp_settings)

    # 3. Clear/restore environment variables
    old_env = dict(os.environ)

    # 4. Reset Notion2API circuit breaker
    from backend.providers.notion2api import _circuit_breaker
    _circuit_breaker.reset()

    yield

    # Restore environment variables
    os.environ.clear()
    os.environ.update(old_env)

    # Clear settings cache again after test
    settings_module._settings_cache = None
    settings_module._settings_mtime = 0.0
