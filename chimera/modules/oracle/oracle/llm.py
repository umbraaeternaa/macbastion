"""Ollama adapter for Mode B classification (§5.3, D2=b / MD-B-1 / MD-B-5).

Thin SYNCHRONOUS wrapper over the `ollama` python lib; the caller (Detector)
wraps each call in asyncio.to_thread (MD-B-5b, consistent with the SQLite
pattern). Structured output via `format=schema` (MD-B-4a). No httpx of our own —
ollama pulls it transitively (§6: our only direct dep here is `ollama`).

GREEN: __init__ stores config; available() probes the daemon; generate() runs a real
ollama call (LlmUnavailableError on failure). `import ollama` at module top makes the
dependency a collection-time requirement (validates `uv add ollama`).
"""

from typing import Any

import ollama  # noqa: F401 — used in GREEN; presence validated at import time


class LlmUnavailableError(Exception):
    """Raised when the Ollama server / model is unreachable (D6 gate)."""


class LlmClient:
    """Thin sync Ollama adapter (§5.3) — GREEN: available()/generate() are real."""

    DEFAULT_MODEL = "llama3.2:1b"  # Q8_0 (pulled); spec §8 left Q4/Q8 open

    def __init__(self, model: str = DEFAULT_MODEL, host: str | None = None) -> None:
        self._model = model
        self._host = host

    @property
    def model(self) -> str:
        return self._model

    def available(self) -> bool:
        """Probe the Ollama server; True iff reachable (D6 startup probe).

        Any failure reaching the server counts as unavailable.
        """
        try:
            ollama.list()
        except Exception:  # noqa: BLE001 — any failure means not reachable
            return False
        return True

    def generate(
        self,
        prompt: str,
        schema: dict[str, Any],
        *,
        temperature: float = 0.0,
        num_predict: int = 200,
    ) -> str:
        """One structured-output generation; return the raw JSON response string.

        Uses Ollama structured output (`format=schema`, MD-B-4a) at temperature 0.
        Raises LlmUnavailableError if the server is unreachable (D6 per-call).
        """
        try:
            result = ollama.generate(
                model=self._model,
                prompt=prompt,
                format=schema,
                options={"temperature": temperature, "num_predict": num_predict},
            )
        except (ConnectionError, ollama.ResponseError) as e:
            raise LlmUnavailableError(str(e)) from e
        return str(result["response"])
