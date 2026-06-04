"""ORACLE (§5.3) — local anomaly detector, observe-first slice.

The first Python CHIMERA module (CHAFF/MIRROR are C). This slice ships Mode A
only: a dual-role daemon that registers with core, serves oracle.*, subscribes
to chaff.* events, and records them into an encrypted baseline. Mode B (LLM
classification via Ollama) is a later slice — there is no detector here yet.
"""

__version__ = "0.4.0-alpha"
