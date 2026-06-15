#!/usr/bin/env python3
"""CHIMERA dead-man demo — a terminal-style reenactment of the REAL reflex audit trail.

No physical recording (macOS won't screen-record the lock screen). The events + timestamps are
REAL (from `chimera audit` — the live dead-man runs); this is a clean visualization of that
actual sequence, generated frame-by-frame with PIL and assembled by ffmpeg. Silent on purpose.

  demo_deadman.py [--frame TS]   # --frame renders one PNG at time TS to /tmp (smoke test)
"""
from __future__ import annotations

import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

W, H, FPS, DUR = 1280, 720, 30, 31.0
FONT = ("/opt/anaconda3/pkgs/matplotlib-base-3.8.4-py312hd77ebd4_0/lib/python3.12/"
        "site-packages/matplotlib/mpl-data/fonts/ttf/DejaVuSansMono.ttf")
OUT_DIR = "/tmp/deadman_frames"
FINAL = "/Users/macbook/Downloads/#1/MD/video md/CHIMERA_deadman_demo.mp4"

BG = (13, 17, 23); BAR = (26, 31, 40); TXT = (214, 226, 232); DIM = (110, 126, 138)
CYAN = (86, 206, 233); GREEN = (80, 224, 140); AMBER = (255, 182, 72); RED = (255, 96, 96)
MAG = (255, 86, 158); WHITE = (238, 246, 250)

f_body = ImageFont.truetype(FONT, 30)
f_h = ImageFont.truetype(FONT, 44)
f_big = ImageFont.truetype(FONT, 72)
f_small = ImageFont.truetype(FONT, 22)
f_lock = ImageFont.truetype(FONT, 64)


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def fade(t, t0, t1, t2, t3):
    if t < t0 or t > t3:
        return 0.0
    if t < t1:
        return ease((t - t0) / (t1 - t0))
    if t < t2:
        return 1.0
    return 1.0 - ease((t - t2) / (t3 - t2))


def blend(c, a):
    return tuple(int(BG[i] + (c[i] - BG[i]) * a) for i in range(3))


def seg(d, x, y, segs, font, a=1.0):
    cx = x
    for txt, col in segs:
        d.text((cx, y), txt, font=font, fill=blend(col, a))
        cx += d.textlength(txt, font=font)
    return cx


def center(d, y, text, font, col, a):
    if a <= 0.02:
        return
    w = d.textlength(text, font=font)
    d.text(((W - w) / 2, y), text, font=font, fill=blend(col, a))


def header(d):
    d.rectangle([0, 0, W, 56], fill=BAR)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([26 + i * 28, 20, 26 + i * 28 + 16, 36], fill=c)
    d.text((W / 2 - 150, 16), "chimera — proximity dead-man", font=f_small, fill=DIM)


def caption(d, t, text, t0, t1, t2, t3, col=WHITE):
    center(d, H - 96, text, f_h, col, fade(t, t0, t1, t2, t3))


def cur(t):
    return "_" if int(t * 2) % 2 == 0 else " "


def render_frame(t):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    header(d)
    x0, y0, lh = 70, 120, 50

    # SCENE 1 (0–4): chimera status
    a1 = fade(t, 0.2, 0.7, 3.4, 4.0)
    if a1 > 0.02:
        seg(d, x0, y0, [("$ ", DIM), ("chimera status", WHITE), (" " + cur(t), GREEN)], f_body, a1)
        if t > 1.4:
            ao = fade(t, 1.4, 1.8, 3.4, 4.0)
            seg(d, x0, y0 + lh, [("  core ", DIM), ("running", GREEN), ("   ·   8 / 8 organs up", DIM)], f_body, ao)
        caption(d, t, "your phone is in the room — your Mac is open", 1.8, 2.4, 3.3, 4.0, DIM)

    # SCENE 2 (4–8): watch, PRESENT
    a2 = fade(t, 4.0, 4.5, 7.4, 8.0)
    if a2 > 0.02:
        seg(d, x0, y0, [("$ ", DIM), ("chimera watch", WHITE)], f_body, a2)
        if t > 5.2:
            ao = fade(t, 5.2, 5.6, 7.4, 8.0)
            seg(d, x0, y0 + lh, [("  ● companion ", DIM), ("PRESENT", GREEN),
                                 ("   rssi ", DIM), ("-58 dBm", CYAN)], f_body, ao)
        caption(d, t, "you walk away with your phone…", 6.3, 6.9, 7.4, 8.0, WHITE)

    # SCENE 3 (8–13): absent -> vault.lock
    a3 = fade(t, 8.0, 8.5, 12.4, 13.0)
    if a3 > 0.02:
        seg(d, x0, y0, [("$ ", DIM), ("chimera watch", WHITE)], f_body, a3)
        if t > 8.8:
            seg(d, x0, y0 + lh, [("  10:24:21  ", CYAN), ("tether.absent", AMBER),
                                 ("    → ", DIM), ("vault.lock", WHITE), ("   ok", GREEN)],
                f_body, fade(t, 8.8, 9.3, 12.4, 13.0))
        if t > 10.2:
            seg(d, x0, y0 + lh * 2, [("  10:24:27  ", CYAN), ("tether.escalation", AMBER),
                                     ("  → ", DIM), ("shim.lock", WHITE), ("   ok", GREEN)],
                f_body, fade(t, 10.2, 10.7, 12.4, 13.0))
        caption(d, t, "phone gone → CHIMERA locks your Mac", 9.4, 10.0, 12.4, 13.0, AMBER)

    # SCENE 4 (13–18.5): MAC LOCKED
    al = fade(t, 13.0, 13.6, 17.6, 18.5)
    if al > 0.02:
        d.rectangle([0, 56, W, H], fill=blend((4, 5, 9), al))
        cx, cy = W // 2, H // 2 - 40
        s = 66
        sr = int(s * 0.55)
        col = blend(MAG, al)
        bh = int(s * 1.4)
        # body
        d.rounded_rectangle([cx - s, cy, cx + s, cy + bh], radius=16, outline=col, width=10)
        # keyhole
        d.ellipse([cx - 9, cy + int(bh * 0.30), cx + 9, cy + int(bh * 0.30) + 18], fill=col)
        d.rectangle([cx - 4, cy + int(bh * 0.30) + 12, cx + 4, cy + int(bh * 0.60)], fill=col)
        # CLOSED shackle: top arch + two legs entering the body
        at = cy - s
        d.arc([cx - sr, at, cx + sr, at + 2 * sr], 180, 360, fill=col, width=10)
        d.line([cx - sr, at + sr, cx - sr, cy], fill=col, width=10)
        d.line([cx + sr, at + sr, cx + sr, cy], fill=col, width=10)
        center(d, cy + bh + 46, "MAC LOCKED", f_big, MAG, al)
        center(d, cy + bh + 132, "vault sealed · screen locked", f_h, WHITE, al * 0.9)

    # SCENE 5 (18.5–24.5): recovered, but stays locked
    a5 = fade(t, 18.7, 19.3, 23.8, 24.5)
    if a5 > 0.02:
        seg(d, x0, y0, [("$ ", DIM), ("chimera watch", WHITE)], f_body, a5)
        if t > 19.6:
            seg(d, x0, y0 + lh, [("  10:24:51  ", CYAN), ("tether.recovered", GREEN),
                                 ("  → ", DIM), ("stand-down", WHITE), ("   ok", GREEN)],
                f_body, fade(t, 19.6, 20.1, 23.8, 24.5))
        if t > 20.8:
            ao = fade(t, 20.8, 21.3, 23.8, 24.5)
            seg(d, x0, y0 + lh * 2, [("  but the screen stays locked — ", DIM),
                                     ("only your password opens it", WHITE)], f_body, ao)
        caption(d, t, "PROXIMITY IS A KEY THAT ONLY LOCKS", 21.4, 22.0, 23.8, 24.5, MAG)

    # SCENE 6 (24.5–31): end card
    ae = fade(t, 24.7, 25.4, 30.4, 31.0)
    if ae > 0.02:
        center(d, 150, "CHIMERA", f_big, WHITE, ae)
        center(d, 250, "a local-first security organism for macOS", f_h, CYAN, ae)
        center(d, 360, "local · no telemetry · no recovery paths", f_body, DIM, ae)
        # the real audit trail, small
        rows = [
            "10:24:21  tether.absent      → vault.lock   ok",
            "10:24:27  tether.escalation  → shim.lock    ok",
            "10:24:51  tether.recovered   → stand-down   ok",
        ]
        for i, r in enumerate(rows):
            center(d, 440 + i * 36, r, f_small, blend(GREEN, ae * 0.85), 1.0)
        center(d, 600, "github.com/umbraaeternaa/macbastion", f_body, AMBER, ae)
    return img


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--frame":
        ts = float(sys.argv[2])
        p = f"/tmp/deadman_smoke_{ts:.0f}.png"
        render_frame(ts).save(p)
        print("wrote", p)
        return
    os.makedirs(OUT_DIR, exist_ok=True)
    n = int(DUR * FPS)
    for i in range(n):
        render_frame(i / FPS).save(f"{OUT_DIR}/f{i:04d}.png")
    print(f"rendered {n} frames")
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
        "-i", f"{OUT_DIR}/f%04d.png", "-c:v", "libx264", "-crf", "18",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", FINAL,
    ], check=True)
    print("DONE:", FINAL)


if __name__ == "__main__":
    main()
