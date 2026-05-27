# §5.3 ORACLE — Anomaly Detector (Brain)

Module: `oracle`
Codename origin: Oracle of Delphi — speaks truth about hidden patterns, but does not act
Status: **Planned** (third CHIMERA module, the brain that observes)
Target version: chimera v0.4.0
Estimated effort: 3-4 working sessions (~12 hours)

---

## 1. Mission

Local LLM-based reasoning engine that detects behavioral and system anomalies by observing patterns across other CHIMERA modules.

ORACLE is the "wise observer" of CHIMERA — it watches, reasons, and warns. It does NOT block actions or override user decisions. Its job is to spot what's unusual and surface that knowledge to the core, which then decides what to do.

This is the first true "brain" component: while CHAFF and ECHO are reflexes (always-on traffic shaping), ORACLE is consciousness (situational reasoning).

---

## 2. Why unique

The privacy/security landscape currently splits into two camps:

- **Rule-based security tools** (Little Snitch, LuLu, pf, traditional IDS): every detection is hand-coded as "if X then alert". They cannot detect what their authors did not anticipate.
- **Cloud-AI security** (CrowdStrike, SentinelOne, Microsoft Defender): use ML, but centralized — they see all users, your data leaves your machine, vendor sees your patterns.
- **Local LLM tools** (Ollama-based projects, LM Studio): used for chat, coding assistance, summarization — but not for security reasoning. Nobody has wired a local LLM to act as a security brain on macOS.

ORACLE differs by combining four properties no existing tool has together:

1. **Reasoning, not matching.** LLM explains why something is unusual, not just flags it.
2. **Local-only.** Llama runs entirely on the user's M2 chip. No vendor sees the events.
3. **Module-aware.** Observes events from CHAFF, ECHO, MIRROR, PULSE, etc. — sees the whole organism, not just network or just processes.
4. **Personal baseline.** Learns YOUR normal patterns, not generic ones. What's normal for a developer at 3am is abnormal for an accountant.

This is the first local-LLM-as-security-brain on macOS, open-source or otherwise.

---

## 3. Algorithm

ORACLE operates in two interleaved modes.

### Mode A — Pattern learning (continuous, passive)
on each event received from core:
record {
timestamp_utc,
source_module,           # chaff, echo, mirror, pulse, etc.
event_type,              # request.sent, anomaly, config.changed
event_payload,           # module-specific JSON
context_snapshot,        # current state of other modules
}

every N events (default 100):
build embeddings of recent event sequences
update baseline model in encrypted SQLite
emit oracle.baseline.updated event

Baseline is the user's "normal day": which modules emit which events at which hours, in which sequences.

### Mode B — Anomaly detection (real-time, active)
on each new event:
context = last 50 events + current module states
prompt = format_for_llm(event, context, baseline)

response = ollama.generate(
model="llama3.2:1b",
prompt=prompt,
temperature=0.0,
max_tokens=200
)

# response includes: score (0-1) + reasoning (text)
score, reasoning = parse_llm_response(response)

if score >= threshold:
emit oracle.anomaly.detected {
severity: score,
reasoning: reasoning,
event: event,
similar_past_events: top_3_baseline_matches
}

The LLM is asked specific questions like:
*"Given the user's normal pattern of {baseline_summary}, is the following event unusual? Event: {event}. Score 0-1 and explain."*

Default threshold: 0.7. Configurable via IPC.

---

## 4. Stack

| Component       | Tech                            | Reason                                            |
|-----------------|---------------------------------|---------------------------------------------------|
| Core daemon     | Python 3.11+ asyncio            | First non-C module; LLM I/O is async-heavy        |
| LLM runtime     | Ollama (HTTP API on localhost:11434) | Mature, easy setup, swappable models         |
| Model           | Llama 3.2 1B Instruct (Q4_K_M)  | ~1.3 GB, 50-200ms inference on M2, "good enough"  |
| Baseline store  | SQLite + Fernet (AES-128)       | Encrypted at rest, queryable, atomic              |
| Embeddings      | sentence-transformers (optional)| For semantic event similarity (v2)                |
| IPC with core   | UNIX socket + JSON-RPC 2.0      | Same protocol as CHAFF/ECHO                       |
| Build system    | pip + venv                      | Standard Python; no compilation needed            |

**Why Python, not C:** LLM I/O is the bottleneck, not Python overhead. Ollama HTTP calls take 50-200ms; Python overhead is microseconds. The simplicity of asyncio + httpx wins.

**Why Ollama, not llama.cpp directly:** Ollama abstracts model management, quantization, GPU/Metal usage. We trade ~30% performance for 90% less code. If performance becomes critical, swap to llama.cpp without changing IPC API.

**Why 1B not 3B:** 1B fits in cache, runs at 100+ tokens/sec on M2, leaves RAM for the rest of the system. Sufficient for binary classification with reasoning. 3B is a future optimization if accuracy needs raising.

---

## 5. IPC API

### Commands (core → oracle)

| Method                    | Params                              | Returns                                          |
|---------------------------|-------------------------------------|--------------------------------------------------|
| `oracle.status`           | none                                | `{model, baseline_events, classifications_today}`|
| `oracle.observe`          | `{source, event_type, payload}`     | `{ok}` — pushes event for learning               |
| `oracle.classify`         | `{event}` (one-shot question)       | `{score, reasoning, similar_events}`             |
| `oracle.baseline.export`  | none                                | `{baseline_summary}` (sanitized)                 |
| `oracle.baseline.reset`   | none                                | `{ok}` — start fresh learning                    |
| `oracle.threshold.set`    | `{threshold: 0.0-1.0}`              | `{config}`                                       |
| `oracle.model.swap`       | `{model_name}`                      | `{ok}` — change Ollama model (e.g. 1b → 3b)      |

### Events (oracle → core)

| Event                       | Payload                                                    |
|-----------------------------|------------------------------------------------------------|
| `oracle.anomaly.detected`   | `{severity, reasoning, event, similar_past_events}`        |
| `oracle.baseline.updated`   | `{event_count, baseline_summary}`                          |
| `oracle.classification.slow`| `{event_id, duration_ms}` — fired if inference > 1000ms    |
| `oracle.error`              | `{code, message, recoverable: bool}`                       |

---

## 6. Dependencies

System:
- Ollama installed (`brew install ollama`)
- Llama 3.2 1B model pulled (`ollama pull llama3.2:1b`)
- ~1.5 GB free disk (model + state + logs)
- ~1 GB RAM during inference (peak)

Python (in chimera's venv):
- `httpx` — async HTTP for Ollama API
- `cryptography` — Fernet encryption for baseline DB
- `pydantic` — event schema validation
- Standard library: `asyncio`, `sqlite3`, `json`, `logging`

Project-internal:
- `~/.config/chimera/oracle/baseline.db` — encrypted SQLite
- `~/.config/chimera/oracle/prompts/` — LLM prompt templates
- IPC socket via core (no direct sockets)

Network: ORACLE makes NO outbound network calls. All Ollama traffic is localhost-only.

---

## 7. Security model

### Protects against
- Slow attacks that evade rule-based detection (gradual permission creep, slow data exfiltration)
- Behavioral drift from user's normal patterns (someone using the machine pretending to be the user)
- Zero-day threats (no signature database needed — anomaly is anomaly)
- Coordinated attacks across modules (e.g. CHAFF profile manipulation + sudden network surge)

### Does NOT protect against
- Prompt injection from event payloads (mitigated by structured prompts + input sanitization, not eliminated)
- Hardware-level compromise (if M2 is compromised, the LLM itself is suspect)
- Adversarial inputs designed to fool the specific Llama version
- False negatives — slow attacks that mimic baseline perfectly

### Threat model assumptions
- Adversary cannot read Llama model weights (they're public, but adversary lacks user's baseline)
- Adversary cannot tamper with baseline DB (encrypted, integrity-checked)
- LLM inference is treated as advisory, not authoritative — core decides action

---

## 8. Open questions

These need decisions before implementation begins:

- **Quantization trade-off.** Q4_K_M (default) vs Q8_0: Q8 is ~2× memory but ~10-15% more accurate. Worth it?
- **Temperature.** 0.0 (deterministic, same answer every time) vs 0.3 (slight creativity). For security reasoning, deterministic feels safer, but might miss edge cases.
- **Context window size.** How many past events to feed into each classification? 10? 50? 200? Trade-off: more context = better reasoning but slower inference.
- **Prompt template strategy.** One generic prompt for all events vs specialized per module (CHAFF-specific, ECHO-specific). Specialized = more accurate, more maintenance.
- **Cold start problem.** First 7 days have no baseline. What does ORACLE do? Stay silent? Use generic patterns? Use a small bootstrap dataset?
- **LLM output reliability.** Llama 1B sometimes returns malformed JSON. Retry? Fall back to score 0.5? Skip event?

To be resolved during implementation.

---

## 9. Status

**Planned.** No code yet.

Depends on:
- CHAFF and ECHO being implemented (to have events to observe)
- Core orchestrator with IPC infrastructure
- Ollama installed and Llama 3.2 1B pulled

This is the first **brain** module. After ORACLE works, the rest of the modules (MIRROR, PULSE, VAULT, TETHER, PURGE) can be implemented in any order because they all talk to core, and core relays to ORACLE.

No imitations. No stubs. (See MANIFESTO §4.)
