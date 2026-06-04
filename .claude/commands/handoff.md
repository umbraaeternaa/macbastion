---
description: Generate a session-handoff journal and save it to the operator's external MD folder
allowed-tools: Bash, Read, Glob, Write
---

# /handoff — Session handoff journal

Generate a daily session-handoff journal (a resume snapshot) and save it OUTSIDE
the repo, into the operator's external folder.

NOT to be confused with `CHIMERA_HANDOFF.md` (a separate production spec inside
the repo). This journal is a per-day snapshot of THIS Claude Code session, used
to resume work later.

## Output location

Folder: `/Users/macbook/Downloads/#1/MD/`
File:   `/Users/macbook/Downloads/#1/MD/SESSION_<YYYY-MM-DD>.md`  (date = today)

⚠️ The path contains `#` — ALWAYS wrap the full path in double quotes in every
bash command, or the shell treats `#` as a comment and truncates the path.

⚠️ Use the POSIX path `Downloads`, NOT `Викачане`. "Викачане" is only Finder's
Ukrainian *display name* for the Downloads folder; the real on-disk path is
always `/Users/macbook/Downloads`. Writing to `…/Викачане/…` makes `mkdir`
create a phantom literal "Викачане" folder the operator never sees in Finder.

## Steps

1. **Resolve today's date** (real output needed):
   `date +%Y-%m-%d`

2. **Gather session state** (read-only — NO git writes, NO commit, NO push):
   - `git log --oneline --since="00:00" --until="23:59"` (today's commits) — and
     also `git log --oneline -10` for fuller context if today's list is short
   - Read `chimera/STATE.md` (current snapshot: done / pending / open tails)
   - From the live conversation, distill: what was completed this session, what
     is pending / next steps, open decisions still unlocked, and the engineering
     "catches" (bugs found, off-by-ones, test-vs-impl distinctions, etc.)

3. **Check for an existing journal for today:**
   `ls -la "/Users/macbook/Downloads/#1/MD/SESSION_$(date +%Y-%m-%d).md" 2>/dev/null`
   - If it does NOT exist → create it (Step 4).
   - If it DOES exist → ASK the operator: append as "Session 2" (and 3, …) to the
     same file, or overwrite. Do NOT silently overwrite. Wait for the answer.

4. **Generate the journal** with these sections (English content; headings as
   below). Keep it factual and specific — quote real commit hashes and counts.

   ```
   # Session handoff — <YYYY-MM-DD>

   ## Summary
   <1–2 paragraphs: what this session was about and where it ended>

   ## Commits this session
   - `<hash>` <type(scope): subject>
   - …
   (if none committed today, say so explicitly)

   ## Completed
   - <bullets — what landed and is verified>

   ## Pending / next steps
   - <bullets — what's queued, the immediate next action>

   ## Open decisions / open tails
   - <bullets — unlocked decisions, honest MANIFESTO §4 tails>

   ## Key technical decisions
   - <bullets — decisions made this session and the rationale>

   ## Engineering catches
   - <bullets — bugs/gotchas caught, e.g. macro double-eval, off-by-one, comment
     `*/` closing a block, test-bug-vs-impl-bug calls>

   ## Resumption hint
   - Repo: https://github.com/umbraaeternaa/macbastion (branch: main)
   - Canonical state: `chimera/STATE.md` (read first), then `CLAUDE.md`
   - Next action: <one concrete sentence on how to pick up>
   ```

5. **Ensure the folder exists, then write the file** (mkdir is idempotent; quote
   the path):
   `mkdir -p "/Users/macbook/Downloads/#1/MD"`
   Write the journal to `"/Users/macbook/Downloads/#1/MD/SESSION_<date>.md"`.

6. **Confirm** (real output):
   - Print the full path of the written file
   - `wc -c "/Users/macbook/Downloads/#1/MD/SESSION_<date>.md"` (size)
   - `ls -la "/Users/macbook/Downloads/#1/MD/"` (prove the file is there)

## Rules

- This command performs NO git operations (the journal lives outside the repo).
- Always double-quote the output path (the `#` in `#1`).
- The journal is a daily resume snapshot — distinct from `CHIMERA_HANDOFF.md`.
- Report honestly: if nothing was committed today, say so; don't invent activity.
