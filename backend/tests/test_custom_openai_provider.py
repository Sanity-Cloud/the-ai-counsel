import json
import pytest
import asyncio
from backend.providers.custom_openai import CustomOpenAIProvider

class _FakeResponse:
    def __init__(self, status_code, json_body=None, text="", content_type="application/json"):
        self.status_code = status_code
        self._json = json_body or {}
        self.text = text or json.dumps(self._json)
        self.headers = {"content-type": content_type}

    def json(self):
        return self._json

class _FakeAsyncClient:
    instances: list = []
    responses: list = []

    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        type(self).instances.append(self)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, **kwargs):
        self.kwargs["__url__"] = url
        self.kwargs["__method__"] = "POST"
        self.kwargs.update(kwargs)
        if not type(self).responses:
            raise AssertionError("No scripted response left for httpx call")
        scripted = type(self).responses.pop(0)
        status, body, text = scripted
        return _FakeResponse(status, body, text)

@pytest.fixture
def fake_httpx(monkeypatch):
    _FakeAsyncClient.instances = []
    _FakeAsyncClient.responses = []
    import httpx
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)
    return _FakeAsyncClient

@pytest.fixture
def fake_settings(monkeypatch):
    class FakeSettings:
        custom_endpoint_name = "TestCustom"
        custom_endpoint_url = "https://custom-api.local/v1"
        custom_endpoint_api_key = "test-key"
        rate_limit_max_retries = 2
        rate_limit_base_delay_seconds = 1.0

    from backend import settings as settings_module
    from backend.providers import custom_openai as custom_openai_module

    def fake():
        return FakeSettings()

    monkeypatch.setattr(settings_module, "get_settings", fake)
    monkeypatch.setattr(custom_openai_module, "get_settings", fake)
    return FakeSettings()

@pytest.fixture
def mock_sleep(monkeypatch):
    sleep_calls = []
    async def fake_sleep(seconds):
        sleep_calls.append(seconds)
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    return sleep_calls

@pytest.mark.asyncio
async def test_custom_openai_success(fake_httpx, fake_settings):
    fake_httpx.responses.append((
        200,
        {
            "choices": [{"message": {"content": "hello"}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10},
        },
        "",
    ))

    provider = CustomOpenAIProvider()
    result = await provider.query("custom:my-model", [{"role": "user", "content": "hi"}])
    assert result["error"] is False
    assert result["content"] == "hello"
    assert result["usage"]["total_tokens"] == 10

@pytest.mark.asyncio
async def test_custom_openai_rate_limit_retry_success(fake_httpx, fake_settings, mock_sleep):
    # First call rate-limited, second succeeds
    fake_httpx.responses.extend([
        (429, {}, "Too many requests"),
        (200, {"choices": [{"message": {"content": "finally"}}]}, ""),
    ])

    provider = CustomOpenAIProvider()
    result = await provider.query("custom:my-model", [{"role": "user", "content": "hi"}])
    assert result["error"] is False
    assert result["content"] == "finally"
    assert len(mock_sleep) == 1
    assert mock_sleep[0] >= 1.0  # Base delay * 2^0 + jitter

@pytest.mark.asyncio
async def test_custom_openai_rate_limit_exhausted(fake_httpx, fake_settings, mock_sleep):
    # Max retries = 2, so 3 total attempts
    fake_httpx.responses.extend([
        (429, {}, "Too many requests"),
        (429, {}, "Too many requests"),
        (429, {}, "Too many requests"),
    ])

    provider = CustomOpenAIProvider()
    result = await provider.query("custom:my-model", [{"role": "user", "content": "hi"}])
    assert result["error"] is True
    assert "due to Rate Limit" in result["error_message"]
    assert result["rate_limited"] is True
    assert len(mock_sleep) == 2  # sleep between attempt 1->2 and 2->3

@pytest.mark.asyncio
async def test_custom_openai_auth_error_fails_fast(fake_httpx, fake_settings, mock_sleep):
    # Auth error should fail fast, zero retries
    fake_httpx.responses.append((401, {}, "Unauthorized"))

    provider = CustomOpenAIProvider()
    result = await provider.query("custom:my-model", [{"role": "user", "content": "hi"}])
    assert result["error"] is True
    assert "authentication failed" in result["error_message"]
    assert len(mock_sleep) == 0

@pytest.mark.asyncio
async def test_custom_openai_not_found_fails_fast(fake_httpx, fake_settings, mock_sleep):
    # 404 should fail fast, zero retries
    fake_httpx.responses.append((404, {}, "Model not found"))

    provider = CustomOpenAIProvider()
    result = await provider.query("custom:my-model", [{"role": "user", "content": "hi"}])
    assert result["error"] is True
    assert "model not found" in result["error_message"]
    assert len(mock_sleep) == 0

@pytest.mark.asyncio
async def test_custom_openai_503_rate_limit_retry(fake_httpx, fake_settings, mock_sleep):
    # 503 with notion_429 marker should retry
    fake_httpx.responses.extend([
        (503, {}, "notion_429 error"),
        (200, {"choices": [{"message": {"content": "ok"}}]}, ""),
    ])

    provider = CustomOpenAIProvider()
    result = await provider.query("custom:my-model", [{"role": "user", "content": "hi"}])
    assert result["error"] is False
    assert result["content"] == "ok"
    assert len(mock_sleep) == 1

@pytest.mark.asyncio
async def test_custom_openai_503_no_marker_fails_fast(fake_httpx, fake_settings, mock_sleep):
    # 503 without marker is a non-rate-limit 503, should fail fast
    fake_httpx.responses.append((503, {}, "Service Unavailable"))

    provider = CustomOpenAIProvider()
    result = await provider.query("custom:my-model", [{"role": "user", "content": "hi"}])
    assert result["error"] is True
    assert "API error" in result["error_message"]
    assert len(mock_sleep) == 0
