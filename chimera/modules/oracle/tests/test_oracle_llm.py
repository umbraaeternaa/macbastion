"""Unit: LlmClient — Ollama adapter (§5.3 Mode B, MD-B-5b).

Monkeypatches the `ollama` module so no real server is needed. Against the stub
(available/generate raise NotImplementedError) every assertion fails — RED.
"""

import ollama
import pytest
from oracle.llm import LlmClient, LlmUnavailableError
from oracle.prompt import RESPONSE_SCHEMA


def test_generate_passes_schema_and_options(monkeypatch):
    captured = {}

    def fake_generate(**kwargs):
        captured.update(kwargs)
        return {"response": '{"score": 0.1, "reasoning": "ok"}'}

    monkeypatch.setattr(ollama, "generate", fake_generate)
    client = LlmClient(model="llama3.2:1b")
    out = client.generate("prompt-text", RESPONSE_SCHEMA, temperature=0.0, num_predict=200)
    assert out == '{"score": 0.1, "reasoning": "ok"}'
    assert captured["model"] == "llama3.2:1b"
    assert captured["format"] == RESPONSE_SCHEMA
    assert captured["options"]["temperature"] == 0.0
    assert captured["options"]["num_predict"] == 200


def test_generate_connection_error_raises_unavailable(monkeypatch):
    def boom(**kwargs):
        raise ConnectionError("refused")

    monkeypatch.setattr(ollama, "generate", boom)
    client = LlmClient()
    with pytest.raises(LlmUnavailableError):
        client.generate("p", RESPONSE_SCHEMA)


def test_available_true_when_server_reachable(monkeypatch):
    monkeypatch.setattr(ollama, "list", lambda: {"models": [{"name": "llama3.2:1b"}]})
    assert LlmClient().available() is True


def test_available_false_when_unreachable(monkeypatch):
    def boom():
        raise ConnectionError("refused")

    monkeypatch.setattr(ollama, "list", boom)
    assert LlmClient().available() is False
