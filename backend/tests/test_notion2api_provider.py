import contextlib
import json

import pytest

from backend.providers.notion2api import Notion2APIProvider


class _FakeResponse:
    def __init__(
        self,
        status_code,
        json_body=None,
        text="",
        content_type="application/json",
        append_done=True,
    ):
        self.status_code = status_code
        self._json = json_body or {}
        self.text = text or json.dumps(self._json)
        self.headers = {"content-type": content_type}
        self.append_done = append_done

    def json(self):
        return self._json

    async def aread(self):
        return self.text.encode("utf-8")

    async def aiter_lines(self):
        for line in self.text.splitlines():
            yield line
        if self.append_done and self.status_code == 200 and "[DONE]" not in self.text:
            yield "data: [DONE]"


class _FakeAsyncClient:
    instances = []
    responses = []

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
            raise AssertionError("No scripted response left for httpx post")
        status, body, text, *options = type(self).responses.pop(0)
        append_done = options[0] if options else True
        return _FakeResponse(status, body, text, append_done=append_done)

    async def get(self, url, **kwargs):
        self.kwargs["__url__"] = url
        self.kwargs["__method__"] = "GET"
        self.kwargs.update(kwargs)
        if not type(self).responses:
            raise AssertionError("No scripted response left for httpx get")
        status, body, text, *options = type(self).responses.pop(0)
        append_done = options[0] if options else True
        return _FakeResponse(status, body, text, append_done=append_done)

    @contextlib.asynccontextmanager
    async def stream(self, method, url, **kwargs):
        self.kwargs["__url__"] = url
        self.kwargs["__method__"] = method
        self.kwargs.update(kwargs)
        if not type(self).responses:
            raise AssertionError(f"No scripted response left for httpx stream {method}")
        status, body, text, *options = type(self).responses.pop(0)
        append_done = options[0] if options else True
        yield _FakeResponse(status, body, text, append_done=append_done)


@pytest.fixture
def fake_httpx(monkeypatch):
    _FakeAsyncClient.instances = []
    _FakeAsyncClient.responses = []
    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)
    return _FakeAsyncClient


@pytest.fixture
def notion_env(monkeypatch):
    monkeypatch.setenv("NOTION2API_BASE_URL", "http://127.0.0.1:8120/v1")
    monkeypatch.setenv("NOTION2API_API_KEY", "test-token")


@pytest.mark.asyncio
async def test_notion2api_query_uses_dedicated_prefix_and_endpoint(fake_httpx, notion_env):
    fake_httpx.responses.append((
        200,
        {"choices": [{"message": {"content": "ok"}}], "usage": {"total_tokens": 3}},
        "",
    ))
    provider = Notion2APIProvider()
    result = await provider.query(
        "notion2api:claude-opus4.7",
        [{"role": "user", "content": "hi"}],
        temperature=0.2,
    )

    assert result == {"content": "ok", "usage": {"total_tokens": 3}, "error": False}
    sent = fake_httpx.instances[-1].kwargs
    assert sent["__url__"] == "http://127.0.0.1:8120/v1/chat/completions"
    assert sent["headers"]["Authorization"] == "Bearer test-token"
    assert sent["json"]["model"] == "claude-opus4.7"
    assert sent["json"]["messages"] == [{"role": "user", "content": "hi"}]
    assert sent["timeout"] == 1200.0


@pytest.mark.asyncio
async def test_notion2api_get_models_prefixes_and_filters(fake_httpx, notion_env):
    fake_httpx.responses.append((
        200,
        {"data": [
            {"id": "gpt-5.2"},
            {"id": "text-embedding-3-large"},
            {"id": "claude-opus4.7"},
            {"id": ""},
        ]},
        "",
    ))

    models = await Notion2APIProvider().get_models()

    assert [m["id"] for m in models] == [
        "notion2api:claude-opus4.7",
        "notion2api:gpt-5.2",
    ]
    assert all(m["source"] == "notion2api" for m in models)
    assert all(m["provider"] == "Notion2API" for m in models)


@pytest.mark.asyncio
async def test_notion2api_get_models_uses_canonical_metadata_and_deduplicates(fake_httpx, notion_env):
    fake_httpx.responses.append((
        200,
        {"data": [
            {
                "id": "glm-5.2",
                "canonical_id": "baseten-glm-5.2",
                "display_name": "GLM 5.2",
                "model_family": "glm",
                "upstream_host": "baseten",
                "public_name": "glm-5.2",
                "aliases": ["glm-5.2"],
            },
            {
                "id": "baseten-glm-5.2",
                "canonical_id": "baseten-glm-5.2",
                "display_name": "GLM 5.2",
                "model_family": "glm",
                "upstream_host": "baseten",
                "public_name": "glm-5.2",
                "aliases": ["glm-5.2"],
            },
        ]},
        "",
    ))

    models = await Notion2APIProvider().get_models()

    assert models == [{
        "id": "notion2api:baseten-glm-5.2",
        "name": "GLM 5.2 [Notion2API]",
        "display_name": "GLM 5.2",
        "provider": "Notion2API",
        "source": "notion2api",
        "model_family": "glm",
        "upstream_host": "baseten",
        "public_name": "glm-5.2",
        "aliases": ["glm-5.2"],
    }]


@pytest.mark.asyncio
async def test_get_models_returns_live_endpoint_models_only(fake_httpx, notion_env):
    fake_httpx.responses.append((
        200,
        {"data": [
            {"id": "almond-croissant-low", "canonical_id": "almond-croissant-low", "display_name": "Sonnet 4.6"},
            {"id": "apricot-sorbet-high", "canonical_id": "apricot-sorbet-high", "display_name": "Opus 4.7"},
        ]},
        "",
    ))

    models = await Notion2APIProvider().get_models()
    assert {m["id"] for m in models} == {
        "notion2api:almond-croissant-low",
        "notion2api:apricot-sorbet-high",
    }
    assert all("pinned" not in m for m in models)


@pytest.mark.asyncio
async def test_notion2api_query_model_not_found_400_produces_clear_error(fake_httpx, notion_env):
    body = {
        "error": {
            "message": "Unsupported model 'angel-cake-high'.",
            "type": "invalid_request_error",
            "param": None,
            "code": "model_not_found",
        }
    }
    fake_httpx.responses.append((400, body, json.dumps(body)))

    result = await Notion2APIProvider().query(
        "notion2api:angel-cake-high",
        [{"role": "user", "content": "hi"}],
    )

    assert result["error"] is True
    assert result["error_message"] == (
        "Model not found: notion2api:angel-cake-high is no longer available through the "
        "Notion2API provider (HTTP 400 model_not_found). Update your council "
        "configuration to a currently available model."
    )


@pytest.mark.asyncio
async def test_notion2api_query_generic_400_falls_through_to_default_error(fake_httpx, notion_env):
    body = {"error": {"message": "Bad request", "type": "invalid_request_error", "code": "bad_request"}}
    fake_httpx.responses.append((400, body, json.dumps(body)))

    result = await Notion2APIProvider().query(
        "notion2api:gpt-5.2",
        [{"role": "user", "content": "hi"}],
    )

    assert result["error"] is True
    assert result["error_message"].startswith("Notion2API error: 400 - ")
    assert "Model not found:" not in result["error_message"]


@pytest.mark.asyncio
async def test_notion2api_validate_connection_accepts_explicit_url_and_token(fake_httpx, monkeypatch):
    monkeypatch.delenv("NOTION2API_API_KEY", raising=False)
    fake_httpx.responses.append((200, {"data": [{"id": "model-a"}]}, ""))

    result = await Notion2APIProvider().validate_connection(
        "http://localhost:9000/v1",
        "abc",
    )

    assert result["success"] is True
    assert result["message"] == "Connected to Notion2API. Found 1 models."
    sent = fake_httpx.instances[-1].kwargs
    assert sent["__url__"] == "http://localhost:9000/v1/models"
    assert sent["headers"]["Authorization"] == "Bearer abc"


@pytest.mark.asyncio
async def test_notion2api_query_reports_http_error(fake_httpx, notion_env):
    fake_httpx.responses.append((403, {"error": "forbidden"}, "Forbidden"))

    result = await Notion2APIProvider().query(
        "notion2api:gpt-5.2",
        [{"role": "user", "content": "hi"}],
    )

    assert result["error"] is True
    assert "Notion2API error: 403" in result["error_message"]


@pytest.mark.asyncio
async def test_notion2api_query_retries_upstream_empty_response(fake_httpx, notion_env, monkeypatch):
    async def _no_sleep(_delay):
        return None

    monkeypatch.setattr("backend.providers.notion2api.asyncio.sleep", _no_sleep)
    empty_response = {
        "error": {
            "message": "Notion returned empty content.",
            "type": "upstream_empty_response",
            "param": None,
            "code": "NOTION_EMPTY",
            "suggestion": "Send the message again.",
        }
    }
    fake_httpx.responses.extend([
        (503, empty_response, json.dumps(empty_response)),
        (200, {"choices": [{"message": {"content": "retried ok"}}]}, ""),
    ])

    result = await Notion2APIProvider().query(
        "notion2api:claude-opus4.8",
        [{"role": "user", "content": "hi"}],
    )

    assert result == {"content": "retried ok", "usage": None, "error": False}
    assert len(fake_httpx.instances) == 2


@pytest.mark.asyncio
async def test_notion2api_query_retries_stream_without_done(fake_httpx, notion_env, monkeypatch):
    async def _no_sleep(_delay):
        return None

    monkeypatch.setattr("backend.providers.notion2api.asyncio.sleep", _no_sleep)
    partial = json.dumps({"choices": [{"delta": {"content": "partial"}}]})
    fake_httpx.responses.extend([
        (200, {}, partial, False),
        (200, {}, partial, False),
        (200, {}, partial, False),
    ])

    result = await Notion2APIProvider().query(
        "notion2api:grok-build0.1",
        [{"role": "user", "content": "rank"}],
    )

    assert result["error"] is True
    assert "without [DONE] marker" in result["error_message"]
    assert len(fake_httpx.instances) == 3


@pytest.mark.asyncio
async def test_notion2api_query_respects_longer_explicit_timeout(fake_httpx, notion_env):
    fake_httpx.responses.append((
        200,
        {"choices": [{"message": {"content": "ok"}}]},
        "",
    ))

    await Notion2APIProvider().query(
        "notion2api:gpt-5.5",
        [{"role": "user", "content": "hi"}],
        timeout=1800.0,
    )

    assert fake_httpx.instances[-1].kwargs["timeout"] == 1800.0


@pytest.mark.asyncio
async def test_notion2api_query_does_not_persist_without_conversation_id(fake_httpx, notion_env):
    fake_httpx.responses.append((
        200,
        {"choices": [{"message": {"content": "ok"}}]},
        "",
    ))

    await Notion2APIProvider().query(
        "notion2api:claude-opus4.7",
        [{"role": "user", "content": "hi"}],
    )

    sent = fake_httpx.instances[-1].kwargs["json"]
    assert "conversation_id" not in sent
    assert sent["metadata"] == {
        "persist_remote_chat": False,
        "source": "ai-counsel",
    }


@pytest.mark.asyncio
async def test_notion2api_query_persists_with_stable_per_model_conversation_id(fake_httpx, notion_env, monkeypatch):
    from backend.settings import get_settings
    monkeypatch.setattr(get_settings(), "notion2api_persist_chats", True)

    fake_httpx.responses.append((
        200,
        {"choices": [{"message": {"content": "ok"}}]},
        "",
    ))

    await Notion2APIProvider().query(
        "notion2api:claude-opus4.7",
        [{"role": "user", "content": "hi"}],
        conversation_id="conv-123",
    )

    sent = fake_httpx.instances[-1].kwargs["json"]
    assert sent["conversation_id"] == "ai-counsel-conv-123-claude-opus4.7"
    assert sent["metadata"] == {
        "persist_remote_chat": True,
        "source": "ai-counsel",
    }


def _script_success(fake_httpx):
    fake_httpx.responses.append((
        200,
        {"choices": [{"message": {"content": "ok"}}], "usage": {"total_tokens": 3}},
        "",
    ))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model_id",
    [
        "claude-fable-5",
        "notion2api:claude-fable-5",
        "anthropic:claude-fable-5",
    ],
)
async def test_notion2api_omits_temperature_for_fable_models(fake_httpx, notion_env, model_id):
    _script_success(fake_httpx)
    provider = Notion2APIProvider()

    result = await provider.query(
        model_id,
        [{"role": "user", "content": "hi"}],
        temperature=0.4,
    )

    assert result["error"] is False
    captured_payload = fake_httpx.instances[-1].kwargs["json"]
    assert "temperature" not in captured_payload


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model_id",
    [
        "claude-sonnet-4",
        "gpt-5",
    ],
)
async def test_notion2api_omits_temperature_for_fixed_upstream_models(fake_httpx, notion_env, model_id):
    _script_success(fake_httpx)
    provider = Notion2APIProvider()

    await provider.query(
        f"notion2api:{model_id}",
        [{"role": "user", "content": "hi"}],
        temperature=0.4,
    )

    captured_payload = fake_httpx.instances[-1].kwargs["json"]
    assert "temperature" not in captured_payload


@pytest.mark.asyncio
async def test_notion2api_keeps_temperature_for_standard_models(fake_httpx, notion_env):
    _script_success(fake_httpx)
    provider = Notion2APIProvider()

    await provider.query(
        "notion2api:claude-opus4.7",
        [{"role": "user", "content": "hi"}],
        temperature=0.25,
    )

    captured_payload = fake_httpx.instances[-1].kwargs["json"]
    assert captured_payload["temperature"] == 0.25


@pytest.mark.asyncio
async def test_notion2api_query_preserves_finish_reason(fake_httpx, notion_env):
    fake_httpx.responses.append((
        200,
        {
            "choices": [{
                "delta": {"content": "partial output"},
                "finish_reason": "length",
            }],
            "usage": {"total_tokens": 10},
        },
        "",
    ))

    result = await Notion2APIProvider().query(
        "notion2api:grok-4.3",
        [{"role": "user", "content": "rank"}],
        max_output_tokens=16000,
    )

    assert result["content"] == "partial output"
    assert result["finish_reason"] == "length"
    sent = fake_httpx.instances[-1].kwargs["json"]
    assert sent["max_tokens"] == 16000
