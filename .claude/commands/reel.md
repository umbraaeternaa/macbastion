---
description: Generate today's CHIMERA Instagram reel (MP4 + medium description + hashtags) from the session, then close the day
allowed-tools: Bash, Read, Write, Glob
---

# /reel — daily CHIMERA Instagram reel

Generate the day's build-in-public reel: a 45s vertical (1080x1920) MP4 with the
cyberpunk/Interstellar style, the Umbra creature, the 8-module ring, a NEW DnB track
each time, and a closing monobank QR + GitHub. Then produce a MEDIUM Instagram
description (what we did today, what we hit, how we fixed it, where we go next) and
hashtags. This is the LAST ritual of the working day, AFTER `/handoff`.

Pipeline scripts live in `.claude/scripts/`: `reel.py` (SVG frames), `music_dnb.py`
(numpy synth), `render.py` (rasteriser), `build_all.sh` (orchestrator). Style spec:
`/Users/macbook/Downloads/#1/MD/video md/CHIMERA_video (1).md` (§2 colours, §5 caption
tone, §13 honest numbering).

## Preconditions
- Run AFTER `/handoff` (the journal is the source for the description).
- The reel venv + DejaVu font are installed (Phase 0). If `cairosvg` import fails,
  cairo is found via `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`.

## Steps

1. **Confirm intent.** Ask the operator (Ukrainian): "Генерувати відео дня N? (так/ні)".
   Proceed only on yes. (When offered right after /handoff, this is the "agent asks".)

2. **Resolve the day number.** Read `.claude/scripts/reel_day.txt` (the next day N).
   Tell the operator "генерую день N" and let him confirm or correct it. ⚠️ §13:
   the day number is narrative — confirm it, never guess silently.

3. **Read the session truth (read-only):**
   - `chimera/STATE.md` — real test count, which modules are DONE vs started.
   - The latest `/Users/macbook/Downloads/#1/MD/SESSION_<date>.md` — today's story:
     what was the input, what was completed, the engineering catches (what we hit +
     how we fixed it), and the next steps.

4. **Compose `brief.json`** in `.claude/scripts/brief.json` (overrides reel.py BRIEF):
   - `day` (confirmed N), `tests` (real count from STATE),
   - `lit`: indices of FULLY-DONE modules — labels order is
     `[CHAFF, ECHO, ORACLE, MIRROR, PULSE, VAULT, TETHER, PURGE]` (0..7),
   - `focus`: the module index today's work touched (magenta highlight),
   - `modules_done`: count of done, `event`: short ALL-CAPS line of today's work
     (e.g. `PULSE :: BASELINE + ASSESS`), `subtitle`: a short evocative line.

5. **Render (background, ~5 min machine time, video is 45s):**
   `bash .claude/scripts/build_all.sh` with `run_in_background` + sandbox disabled.
   When it completes, read its output: the MP4 path, the QR line (must say `QR OK ->
   https://send.monobank.ua/jar/...`), and the ffprobe dims (1080x1920, ~45s).
   If `QR NOT DECODED` — reduce grain (alls=4 -> 2) or enlarge the QR card, re-run.

6. **Write the description + hashtags.** MEDIUM length (not terse), per the §5 tone:
   engineering precision, concrete facts + real numbers, NO marketing words
   ("revolutionary"/"game-changer"/emoji-spam). Structure:
   - EN main: today's input -> what shipped -> what we hit + how we fixed it (the
     engineering catch) -> the result (tests green) -> where next. End with
     "Built for one operator. No telemetry. No recovery paths." +
     `github.com/umbraaeternaa/macbastion` + "follow the evolution."
   - UA "простими словами" paragraph (для не-технічних).
   - 5-8 hashtags (mix broad + niche): e.g.
     `#infosec #opensource #buildinpublic #appsec #cybersecurity #python #macos`
   Save it next to the video as `..._caption.md` AND show it in chat (paste-ready).

7. **Close the day.** Bump `.claude/scripts/reel_day.txt` to N+1. Report: MP4 path,
   that QR works, and the description/hashtags — then state "Сесію дня N закрито".

## Rules
- All communication with the operator in Ukrainian; explain each command before running.
- Verify day/test numbers against STATE + git, never invent (§13 honest numbering).
- A NEW DnB track every run (build_all.sh uses a random seed by default).
- The video is 45s; "кілька хвилин" only refers to render time, never the video length.
