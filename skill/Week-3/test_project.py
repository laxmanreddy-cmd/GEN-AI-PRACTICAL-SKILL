"""Offline unit tests for the Week 3 monitoring project."""

import pytest
import requests
from unittest.mock import Mock, patch

import main
from cost_calculator import calculate_cost
from llm_client import LLMClient, OllamaProvider


class FakeProvider:
    provider_name = "ollama"
    model = "llama3.2"

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def generate(self, prompt):
        self.calls += 1
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class FakeLogger:
    def __init__(self, fail=False):
        self.documents = []
        self.fail = fail

    def log_request(self, document):
        self.documents.append(document)
        if self.fail:
            raise OSError("simulated MongoDB logging error")


def test_cost_calculator():
    assert calculate_cost("ollama", "llama3.2", 10, 10) == 0.0
    assert calculate_cost("gemini", "unconfigured", 10, 10) is None
    assert calculate_cost("gemini", "gemini-3.8-flash", 1_000_000, 1_000_000) == 0.5


def test_success_is_not_repeated_when_logging_fails(capsys):
    provider = FakeProvider([("answer", 2, 3)])
    logger = FakeLogger(fail=True)

    answer = LLMClient(provider, logger).generate("question")

    assert answer == "answer"
    assert provider.calls == 1
    assert logger.documents[0]["status"] == "success"
    assert logger.documents[0]["total_tokens"] == 5
    assert "could not save" in capsys.readouterr().out


def test_retryable_error_retries_and_records_attempts(monkeypatch):
    monkeypatch.setattr("llm_client.time.sleep", lambda _seconds: None)
    provider = FakeProvider([requests.ConnectionError("temporary"), ("answer", 1, 2)])
    logger = FakeLogger()

    assert LLMClient(provider, logger).generate("question") == "answer"
    assert provider.calls == 2
    assert logger.documents[0]["attempts"] == 2


def test_permanent_error_is_logged_and_raised():
    provider = FakeProvider([RuntimeError("permanent failure")])
    logger = FakeLogger()

    with pytest.raises(RuntimeError, match="permanent failure"):
        LLMClient(provider, logger).generate("question")

    assert provider.calls == 1
    assert logger.documents[0]["status"] == "failed"
    assert logger.documents[0]["error"] == "permanent failure"


def test_invalid_provider_selection(capsys, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _prompt: "9")

    main.main()

    assert "Invalid selection" in capsys.readouterr().out


def test_missing_gemini_key_is_reported(capsys, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setattr("builtins.input", lambda _prompt: "1")

    main.main()

    assert "Gemini API key is missing" in capsys.readouterr().out


def test_missing_ollama_model_has_helpful_message():
    response = Mock()
    response.status_code = 404
    response.raise_for_status.side_effect = requests.HTTPError(response=response)

    with patch("llm_client.requests.post", return_value=response):
        with pytest.raises(RuntimeError, match="ollama pull llama3.2"):
            OllamaProvider().generate("question")
