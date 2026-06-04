"""Ollama adapter for Mode B classification (§5.3, D2=b / MD-B-1 / MD-B-5).

Thin SYNCHRONOUS wrapper over the `ollama` python lib; the caller (Detector)
wraps each call in asyncio.to_thread (MD-B-5b, consistent with the SQLite
pattern). Structured output via `format=schema` (MD-B-4a). No httpx of our own —
ollama pulls it transitively (§6: our only direct dep here is `ollama`).

STUB — RED slice. __init__ stores config; available()/generate() raise
NotImplementedError. `import ollama` at module top makes the dependency a
collection-time requirement (validates `uv add ollama`).
"""

from typing import Any

import ollama  # noqa: F401 — used in GREEN; presence validated at import time


class LlmUnavailableError(Exception):
    """Raised when the Ollama server / model is unreachable (D6 gate)."""


class LlmClient:
    """Thin sync Ollama adapter (§5.3). STUB (RED slice)."""

    DEFAULT_MODEL = "llama3.2:1b"  # Q8_0 (pulled); spec §8 left Q4/Q8 open

    def __init__(self, model: str = DEFAULT_MODEL, host: str | None = None) -> None:
        self._model = model
        self._host = host

    @property
    def model(self) -> str:
        return self._model

    def available(self) -> bool:
        """Probe the Ollama server; True iff reachable (D6 startup probe)."""
        raise NotImplementedError("LlmClient.available — RED slice")

    def generate(
        self,
        prompt: str,
        schema: dict[str, Any],
        *,
        temperature: float = 0.0,
        num_predict: int = 200,
    ) -> str:
        """One structured-output generation; return the raw JSON response string.

        Raises LlmUnavailableError if the server is unreachable (D6 per-call).
        """
        raise NotImplementedError("LlmClient.generate — RED slice")
