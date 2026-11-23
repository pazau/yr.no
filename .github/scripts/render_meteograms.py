#!/usr/bin/env python3
"""Download the yr.no meteogram SVGs, crop each to the next day or two and render
320x240 PNGs for the ESP32.

Output: esp32/meteogram1.png, esp32/meteogram2.png, esp32/meteogram3.png
(served by GitHub Pages at https://<user>.github.io/esp32/meteogramN.png)

Also writes /tmp/preview_N.png (the full render with the crop box in red) so you can
see what was cut off. The workflow uploads these as a downloadable artifact.
"""
import os
import subprocess
import sys

from PIL import Image, ImageDraw

URLS = [
    "https://www.yr.no/nb/innhold/2-2613588/meteogram.svg",
    "https://www.yr.no/nb/innhold/2-2618425/meteogram.svg",
    "https://www.yr.no/nb/innhold/2-2614481/meteogram.svg",
]

# ---------------------------------------------------------------------------
# TUNE THESE.
# CROP = (left, top, right, bottom) as fractions of the full rendered image.
#   (0.0, 0.0, 0.40, 1.0) = keep the left 40 % of the width, full height.
# Time runs left to right, so a smaller "right" value shows fewer hours, larger.
# If the cut-off edge slices through labels, adjust and re-run the workflow.
# ---------------------------------------------------------------------------
DEFAULT_CROP = (0.0, 0.0, 0.60, 1.0)
CROPS = {          # per-image overrides, keyed by 1, 2, 3
    # 1: (0.0, 0.0, 0.35, 1.0),
}

W, H = 320, 240
RENDER_WIDTH = 2400         # render big, crop, then downscale: sharper text
MAX_BYTES = 45_000          # the ESP32 firmware accepts up to 48 KB
OUT_DIR = "esp32"
UA = "pazau-esp32-display (https://github.com/pazau/pazau.github.io)"


def render(i: int, url: str) -> None:
    svg = f"/tmp/meteogram{i}.svg"
    big = f"/tmp/meteogram{i}.png"

    subprocess.run(
        ["curl", "-fsSL", "--max-time", "30", "-A", UA, "-o", svg, url],
        check=True,
    )
    subprocess.run(
        ["rsvg-convert", "--keep-aspect-ratio", "-w", str(RENDER_WIDTH),
         "-b", "white", "-o", big, svg],
        check=True,
    )

    full = Image.open(big).convert("RGB")
    fw, fh = full.size
    left, top, right, bottom = CROPS.get(i, DEFAULT_CROP)
    box = (round(left * fw), round(top * fh), round(right * fw), round(bottom * fh))

    # Preview: the whole render with the kept region outlined in red.
    preview = full.copy()
    ImageDraw.Draw(preview).rectangle(box, outline=(255, 0, 0), width=6)
    preview.thumbnail((1600, 1600), Image.LANCZOS)
    preview.save(f"/tmp/preview_{i}.png")

    img = full.crop(box)
    img.thumbnail((W, H), Image.LANCZOS)          # fit inside 320x240, keep aspect
    canvas = Image.new("RGB", (W, H), "white")
    canvas.paste(img, ((W - img.width) // 2, (H - img.height) // 2))

    out = os.path.join(OUT_DIR, f"meteogram{i}.png")
    for colors in (256, 128, 64, 32):
        pal = canvas.quantize(colors=colors, method=Image.Quantize.MEDIANCUT,
                              dither=Image.Dither.NONE)
        pal.save(out, optimize=True)              # non-interlaced palette PNG
        size = os.path.getsize(out)
        if size <= MAX_BYTES:
            break
    print(f"{out}: {size} bytes, {colors} colours | full render {fw}x{fh}, "
          f"crop box {box} -> shown at {img.width}x{img.height}")


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
