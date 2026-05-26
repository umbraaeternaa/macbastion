# CLAUDE.md

> This file is read by Claude Code at the start of every session.
> It is the canonical entry point for project context.
>
> Updated: 2026-05-27
> Project: macbastion / CHIMERA
> Owner: Andranik Khachatryan (@umbraaeternaa)

---

## 1. Project identity

You are working on **CHIMERA** — a unified privacy/security organism for macOS.

CHIMERA is NOT a collection of tools. It is **one mind** orchestrating
specialized native modules, each unique on its own, devastating together.

Parent project: `macbastion` (this folder). CHIMERA lives in `chimera/`.

Read first, in this order:
1. `chimera/MANIFESTO.md` — 7-principle philosophy (the law)
2. `chimera/docs/ARCHITECTURE.md` — Part 1 of 5: stack, diagram, principles
3. `chimera/STATE.md` — current snapshot (what's done, what's pending)
4. `chimera/docs/modules/*.md` — module specifications (CHAFF, ECHO, …)

---

## 2. Working principles (from MANIFESTO)

1. **One machine, one owner** — local-first, no cloud, no telemetry
2. **Modules are organs** — each does ONE thing, perfectly
3. **The brain matters more than organs** — coordination creates emergent intelligence
4. **No imitations** — if it doesn't work, say so honestly. Empty function with TODO > stub that pretends
5. **Hybrid stack with reason** — Python (UX), C (syscalls), ARM64 Asm (where it matters)
6. **Open but not for masses** — power tool, not consumer product
7. **Slow is what survives** — we build for a year, not a week

---

## 3. Architecture (current)

```
macbastion/
├── chimera/
│   ├── MANIFESTO.md              ← 7 principles
│   ├── STATE.md                  ← current snapshot
│   ├── core/                     ← future: Python orchestrator
│   ├── modules/                  ← future: 8 native daemons
│   ├── proto/                    ← future: JSON-RPC schemas
│   └── docs/
│       ├── ARCHITECTURE.md       ← Parts 1-5 (currently Part 1)
│       └── modules/
│           ├── CHAFF.md          ← §5.1 (done)
│           ├── ECHO.md           ← §5.2 (done)
│           ├── ORACLE.md         ← §5.3 (next)
│           ├── MIRROR.md         ← §5.4
│           ├── PULSE.md          ← §5.5
│           ├── VAULT.md          ← §5.6
│           ├── TETHER.md         ← §5.7
│           └── PURGE.md          ← §5.8
```

Planned 8 modules (current state in STATE.md):

| # | Module | Lang | Purpose |
|---|--------|------|---------|
| §5.1 | CHAFF | C+Asm | Traffic obfuscator — decoy HTTPS to mask real patterns |
| §5.2 | ECHO | C | Bandwidth normalizer — constant-rate padding |
| §5.3 | ORACLE | Python | Local LLM (Llama 3.2 1B) — anomaly detection |
| §5.4 | MIRROR | C | Behavioral noise injector — humanlike click/type jitter |
| §5.5 | PULSE | C | Cognitive load monitor — detect fatigue, raise confirms |
| §5.6 | VAULT | C | Time-locked storage — files accessible only at scheduled times |
| §5.7 | TETHER | C++ | BT mesh dead-man — pair with phone, auto-panic if separated |
| §5.8 | PURGE | C+Asm | Secure wipe — ARM64 dc zva, cache clear, RAM erase |

---

## 4. Working protocol — surgical mode

Default mode is **surgical**:

- ONE step at a time
- Show the user what you will do BEFORE doing it
- Wait for explicit confirmation before destructive actions
- After each action: confirm what was done and what's next

User shortcut: `+` (just plus sign) means "output matched expectations, proceed".
If user sends only `+` — interpret as "OK, next step".

When real output is required for next step (e.g. git hashes, file lists,
ambiguous results) — say so explicitly: "real output needed, not +".

---

## 5. Code conventions

Markdown specs:
- File-level title: `# §X.Y MODULE_NAME — Short purpose`
- Standard 9 sections per module spec (see CHAFF.md as template):
  Mission, Why unique, Algorithm, Stack, IPC API, Dependencies,
  Security model, Open questions, Status
- ASCII diagrams inside ``` code fences (not ~~~)
- Tables for tabular data
- No emoji in spec headings (emoji ok in body for emphasis)

Code (future):
- C: C17, clang, `-Wall -Wextra -Werror`
- Python: 3.11+, type hints, asyncio for IPC
- ARM64 Asm: AArch64 syntax, comment every instruction
- Naming: `snake_case` for files and functions
- IPC: JSON-RPC 2.0 over UNIX sockets

Commit messages:
- Format: `<type>(<scope>): <subject>`
- Types: feat, fix, docs, chore, refactor, test
- Scope for CHIMERA: `chimera`, or `chimera/<module>` (e.g. `chimera/chaff`)
- Example: `docs(chimera): add ORACLE module specification (§5.3)`

---

## 6. What NOT to do

- Do NOT create stub functions that "look like they work"
- Do NOT make outbound network calls from any CHIMERA module
  EXCEPT CHAFF (its job is to generate traffic)
- Do NOT add dependencies without discussion (Python: stdlib + ollama + cryptography only;
  C: system libs + libcurl only; no Go, Rust, JavaScript)
- Do NOT bypass SIP or recommend disabling it
- Do NOT touch macbastion/ files outside chimera/ without explicit request
  (macbastion has its own modules: stealth, native/mac_spoof, swiftbar)
- Do NOT commit without showing the diff first

---

## 7. Quick references

- GitHub: https://github.com/umbraaeternaa/macbastion
- Owner workflow: macOS 26, M2, FileVault on, SIP on, LuLu deny-by-default
- Python venv: `.venv/` (already exists, use it for any Python work)
- Existing tools in parent project (macbastion):
  - `macbastion scan ports` — port audit CLI
  - `macbastion stealth on/off/status` — hostname rotation
  - `native/mac_spoof/` — MAC address tool (first C module)
  - `swiftbar/` — menu bar plugin

---

## 8. Session start checklist

When starting a new Claude Code session in this folder:

1. Read this file (you're doing it)
2. Read `chimera/STATE.md` (current snapshot)
3. Acknowledge in first message which module/task is next
4. Wait for user direction before any write actions
