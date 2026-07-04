import sys
import types

from ai.admin_provider import (
    GeminiAdminAIProvider,
    admin_ai_provider_status,
    refine_admin_insights,
)


def test_admin_ai_provider_mock_returns_metric_insights(monkeypatch):
    monkeypatch.setenv("ADMIN_AI_PROVIDER", "mock")
    insights = [{"type": "peak", "text": "Peak hour is 19:00", "metrics": {"hour": 19}}]

    result = refine_admin_insights(metrics={"orders": 10}, insights=insights)

    assert result.provider == "mock"
    assert result.fallback_used is False
    assert result.insights == insights


def test_admin_ai_provider_falls_back_when_key_missing(monkeypatch):
    monkeypatch.setenv("ADMIN_AI_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    insights = [{"type": "revenue", "text": "Revenue is metric-backed.", "metrics": {}}]

    result = refine_admin_insights(metrics={}, insights=insights)

    assert result.provider == "mock"
    assert result.fallback_used is True
    assert "OPENAI_API_KEY" in (result.error or "")
    assert result.insights == insights


def test_admin_ai_provider_status_for_unknown_provider(monkeypatch):
    monkeypatch.setenv("ADMIN_AI_PROVIDER", "unknown")

    status = admin_ai_provider_status()

    assert status["provider"] == "unknown"
    assert status["configured"] is False
    assert status["fallback_provider"] == "mock"


def test_gemini_provider_normalizes_google_model_name():
    provider = GeminiAdminAIProvider(
        api_key="test-key", model="models/gemini-2.5-flash"
    )

    assert provider.model == "gemini-2.5-flash"


def test_admin_ai_provider_extracts_json_array_from_provider_text(monkeypatch):
    monkeypatch.setenv("ADMIN_AI_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class FakeMessage:
        content = 'Here is the result:\n[{"type":"peak","text":"Peak hour improved."}]'

    class FakeChoice:
        message = FakeMessage()

    class FakeCompletions:
        @staticmethod
        def create(**kwargs):
            return type("FakeResponse", (), {"choices": [FakeChoice()]})()

    class FakeClient:
        def __init__(self, **kwargs):
            self.chat = type("FakeChat", (), {"completions": FakeCompletions()})()

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeClient))

    result = refine_admin_insights(
        metrics={},
        insights=[{"type": "peak", "text": "Peak hour original.", "metrics": {}}],
    )

    assert result.provider == "openai"
    assert result.fallback_used is False
    assert result.insights[0]["text"] == "Peak hour improved."
