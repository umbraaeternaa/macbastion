---
description: Generate today's CHIMERA Instagram reel (MP4 + medium description + hashtags) from the session, then close the day
allowed-tools: Bash, Read, Write, Glob, WebSearch
---

# /reel — daily CHIMERA Instagram reel

Generate the day's build-in-public reel: a 45s vertical (1080x1920) MP4 in the evolving
cyberpunk→**anime cel-shaded** style (see Creative direction), with the Umbra creature, the
8-module ring, a NEW **beautiful, trend-checked** track each time, and a closing monobank QR +
GitHub. Then produce a MEDIUM Instagram description (what we did today, what we hit, how we
fixed it, where we go next) and hashtags. This is the LAST ritual of the working day,
AFTER `/handoff`.

Pipeline scripts live in `.claude/scripts/`: `reel.py` (SVG frames), `music.py`
(numpy/scipy multi-genre synth — 14 band genres + jazz/blues/classical engines; random
genre x key x scale x progression x tempo + a generated melody each run), `render.py`
(rasteriser), `build_all.sh` (orchestrator). Style spec:
`/Users/macbook/Downloads/#1/MD/video md/CHIMERA_video (1).md` (§2 colours, §5 caption
tone, §13 honest numbering).

## Creative direction — EVOLVE EVERY DAY (operator directive, standing — Day 22 intensified)

The reel is NOT a fixed template. **Every day it must CHANGE and GROW — boldly, with maximum
evolution, colour, dynamism and motion.** Never repeat the same frames; add or swap elements
each time and push FURTHER than yesterday. Keep it logical and readable — but bright, daring,
multifaceted, innovative, hi-tech, alive.

### Look — toward Japanese ANIME / a real animated film (мультфільм)

The house style EVOLVES from cyberpunk motion-graphics TOWARD a cel-shaded **anime / cartoon**
feel. Each run, push the look in that direction:

- **Cel shading:** flat colour fills + hard ink outlines (not only neon strokes); bold,
  saturated anime palettes; gradient anime skies / cosmic backdrops.
- **Anime FX:** speed lines, impact/flash frames on the beat, lens flare + bloom, sakura
  petals / embers / floating particles, light rays, "manga" cut-in panels.
- **An expressive Umbra:** redraw the creature with a large reflective anime eye and real
  emotion/expression; sakuga-style flowing cloak/hair sway; a readable character, not a blob.
- **Maximum movement:** more camera energy, parallax, smear frames, beat-synced motion — the
  frame should feel alive and animated, like a real cartoon, not a static diagram.

Keep the established canon as the WORLD inside that anime look: the Umbra creature, the
8-module arsenal ring (per-module glyphs + readouts), the Interstellar black-hole core, the
neural-net "mind" layer, the operator HUD console (telemetry/gauges/oscilloscope), data
streams. Draw FREELY from hi-tech · physics · quantum physics · mechanics · ALL programming
languages · galaxies · deep space · depth · rich colour as your toolbox.

### Sound — beautiful, varied, IN-TREND music (check the trends every run)

`music.py` is a local multi-genre synth (numpy/scipy, royalty-free, no cloud). BEFORE
composing, **WebSearch the current music trends** — what BPM / genres / sub-styles are
charting now — and let that steer the pick. Choose from the full roster:
pop · techno · drum-n-bass · jungle · deep house · deep progressive · electronic/electro ·
new wave · indie · indie-pop · **jazz · blues · classical** (`music.py --genre NAME`; omit
to randomise). Aim for a track that is genuinely DIFFERENT every run AND genuinely BEAUTIFUL /
likeable / on-trend — real melody + warm timbres, not just a beat over a riff.

### Discipline

Reuse the proven scaffold (camera, fades, QR, timeline, `variant_seed` daily palette/camera
rotation) but bring something genuinely NEW each day — a new element, scene, motif, or one step
further into the anime look. ALWAYS smoke-test a few `reel.frame(ts)` PNGs via Read BEFORE the
full ~8-12 min render, and self-review the look. HONESTY (§4): this is trend-INFORMED
*procedural* art + on-device synthesis — not sampled music or AI-generated anime frames. Push
the craft; never fake the source.

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
   First WebSearch the current music trend (see "Sound" above) and, if a clear genre fits,
   set it in `build_all.sh`'s `music.py` call (`--genre NAME`); otherwise let it randomise.
   Then `bash .claude/scripts/build_all.sh` with `run_in_background` + sandbox disabled.
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
- A genuinely DIFFERENT **and beautiful** track every run — WebSearch current trends first,
  then `music.py` (genre x key x scale x progression x tempo + melody; 14 band genres + the
  jazz/blues/classical engines), NOT just a new beat over the same riff (the day-12 fix).
- EVOLVE the visuals every day toward the **anime/cartoon** look (see "Creative direction") —
  never ship the same frames; more colour, motion and boldness than yesterday.
- The video is 45s; "кілька хвилин" only refers to render time, never the video length.
