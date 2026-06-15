#!/bin/bash
# Full CHIMERA reel build: new DnB track -> 1080 SVG frames (45s) -> ffmpeg (grain +
# music) -> final MP4 in the operator's "video md" folder. New track every run.
# Day/event come from brief.json (written by the /reel command).
set -e
cd ~/Projects/macbastion/.claude/scripts
PY=.venv/bin/python
DUR=45; FPS=24; NF=$((DUR * FPS))
OUT="/Users/macbook/Downloads/#1/MD/video md"
DAY=$($PY -c "import json;print(json.load(open('brief.json'))['day'])" 2>/dev/null || echo "x")
STAMP=$(date +%Y-%m-%d_%H%M%S)
FINAL="$OUT/CHIMERA_reel_day${DAY}_${STAMP}.mp4"
WORK=$(mktemp -d)
mkdir -p "$OUT" "$WORK/frames"

echo "[1/4] synth new track (${DUR}s, ${GENRE:-RANDOM} genre + seed)"
$PY music.py --dur $DUR --out "$WORK/track.wav" ${GENRE:+--genre "$GENRE"}

echo "[2/4] render $NF SVG frames"
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib $PY render.py 0 $NF "$WORK/frames" qr_matrix.png

echo "[3/4] assemble: PNG -> H.264 + film grain + AAC music"
ffmpeg -y -loglevel error -framerate $FPS -i "$WORK/frames/f%04d.png" -i "$WORK/track.wav" \
  -vf "noise=alls=3:allf=t,format=yuv420p" -c:v libx264 -crf 22 -preset medium \
  -movflags +faststart -c:a aac -b:a 192k -shortest "$FINAL"

echo "[4/4] verify QR decodes (threshold method)"
$PY - "$FINAL" <<'PY' || echo "QR check error"
import sys, cv2
cap = cv2.VideoCapture(sys.argv[1]); cap.set(cv2.CAP_PROP_POS_MSEC, 41500)
ok, fr = cap.read()
res = "NO FRAME"
if ok:
    g = cv2.cvtColor(fr[521:885, 225:589], cv2.COLOR_BGR2GRAY)  # QR card @810x1440 (1080-coords x0.75)
    g = cv2.resize(g, (620, 620), interpolation=cv2.INTER_CUBIC)
    _, th = cv2.threshold(g, 120, 255, cv2.THRESH_BINARY)
    d, _, _ = cv2.QRCodeDetector().detectAndDecode(th)
    res = ("QR OK -> " + d) if d else "QR NOT DECODED (reduce grain / enlarge card)"
print(res)
PY

rm -rf "$WORK"
echo "DONE: $FINAL"
ffprobe -v error -show_entries format=duration,size -show_entries stream=width,height -of default=noprint_wrappers=1 "$FINAL"
