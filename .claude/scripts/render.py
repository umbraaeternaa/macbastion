#!/usr/bin/env python3
"""Rasterise reel.frame(ts) -> PNG frames via cairosvg.

MUST be run with DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib so cairocffi finds the
Homebrew libcairo (macOS doesn't search /opt/homebrew/lib by default).

Usage: render.py <start_frame> <end_frame> <outdir> [qr_png]
Renders frames [start, end) at reel.FPS as outdir/fNNNN.png.
"""

import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cairosvg  # noqa: E402

import reel  # noqa: E402


def main() -> None:
    start, end, outdir = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    qr = sys.argv[4] if len(sys.argv) > 4 else ""
    if qr and Path(qr).exists():
        reel.BRIEF["qr_png"] = base64.b64encode(Path(qr).read_bytes()).decode()
    Path(outdir).mkdir(parents=True, exist_ok=True)
    for f in range(start, end):
        ts = f / reel.FPS
        cairosvg.svg2png(
            bytestring=reel.frame(ts).encode(),
            write_to=f"{outdir}/f{f:04d}.png",
            output_width=reel.W,
            output_height=reel.H,
        )
    print(f"rendered {start}..{end} -> {outdir}")


if __name__ == "__main__":
    main()
