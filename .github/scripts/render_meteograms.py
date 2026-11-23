#!/usr/bin/env python3
"""Download the yr.no meteogram SVGs and render them as small 320x240 PNGs for the ESP32.

Output: esp32/meteogram1.png, esp32/meteogram2.png, esp32/meteogram3.png
(served by GitHub Pages at https://<user>.github.io/esp32/meteogramN.png)
"""
import os
import subprocess
import sys

from PIL import Image

URLS = [
    "https://www.yr.no/nb/innhold/2-2613588/meteogram.svg",
    "https://www.yr.no/nb/innhold/2-2618425/meteogram.svg",
    "https://www.yr.no/nb/innhold/2-2614481/meteogram.svg",
]
W, H = 320, 240
MAX_BYTES = 40_000          # the ESP32 firmware accepts up to 48 KB; stay below it
OUT_DIR = "esp32"
UA = "pazau-esp32-display (https://github.com/pazau/pazau.github.io)"


def render(i: int, url: str) -> None:
    svg = f"/tmp/meteogram{i}.svg"
    big = f"/tmp/meteogram{i}.png"

    subprocess.run(
        ["curl", "-fsSL", "--max-time", "30", "-A", UA, "-o", svg, url],
        check=True,
    )
    # Render large first, then downscale: sharper text than rendering at 320 px directly.
    subprocess.run(
        ["rsvg-convert", "--keep-aspect-ratio", "-w", "1280", "-h", "960",
         "-b", "white", "-o", big, svg],
        check=True,
    )

    img = Image.open(big).convert("RGB")
    img.thumbnail((W, H), Image.LANCZOS)
    canvas = Image.new("RGB", (W, H), "white")
    canvas.paste(img, ((W - img.width) // 2, (H - img.height) // 2))

    out = os.path.join(OUT_DIR, f"meteogram{i}.png")
    for colors in (128, 64, 32):
        pal = canvas.quantize(colors=colors, method=Image.Quantize.MEDIANCUT,
                              dither=Image.Dither.NONE)
        pal.save(out, optimize=True)      # non-interlaced palette PNG
        size = os.path.getsize(out)
        if size <= MAX_BYTES:
            break
    print(f"{out}: {size} bytes, {colors} colours, source image {img.width}x{img.height}")


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    failed = 0
    for i, url in enumerate(URLS, 1):
        try:
            render(i, url)
        except Exception as exc:          # keep the previous image if one download fails
            failed += 1
            print(f"FAILED {url}: {exc}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
