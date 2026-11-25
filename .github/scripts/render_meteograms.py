#!/usr/bin/env python3
"""Download the yr.no meteogram SVGs, crop each to the next day or two and render
320x240 8-bit BMP files for the ESP32 (it streams them straight to the screen, no decoder).

Output: esp32/meteogram1.bmp, esp32/meteogram2.bmp, esp32/meteogram3.bmp
(served by GitHub Pages at https://<user>.github.io/<repo path>/esp32/meteogramN.bmp)

While tuning, it also writes esp32/preview_N.png (the full render with the crop box in
red). When the crop's right edge equals TUNED_RIGHT, no previews are made and any old
ones are deleted. Change the right edge to another value to get previews again.
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
# CROP = (left, top, right, bottom) as fractions of the full rendered image.
#   (0.0, 0.0, 0.60, 1.0) = keep the left 60 % of the width, full height.
# ---------------------------------------------------------------------------
DEFAULT_CROP = (0.0, 0.0, 0.60, 1.0)
CROPS = {          # per-image overrides, keyed by 1, 2, 3
    # 1: (0.0, 0.0, 0.55, 1.0),
}
TUNED_RIGHT = 0.60  # a crop with this right edge is considered final: no previews

W, H = 320, 240
RENDER_WIDTH = 2400         # render big, crop, then downscale: sharper text
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

    preview_path = os.path.join(OUT_DIR, f"preview_{i}.png")
    if abs(right - TUNED_RIGHT) < 1e-9:
        # Final crop: no preview, and remove one left over from earlier tuning.
        if os.path.exists(preview_path):
            os.remove(preview_path)
    else:
        preview = full.copy()
        ImageDraw.Draw(preview).rectangle(box, outline=(255, 0, 0), width=6)
        preview.thumbnail((1600, 1600), Image.LANCZOS)
        preview.save(preview_path, optimize=True)

    img = full.crop(box)
    img.thumbnail((W, H), Image.LANCZOS)          # fit inside 320x240, keep aspect
    canvas = Image.new("RGB", (W, H), "white")
    canvas.paste(img, ((W - img.width) // 2, (H - img.height) // 2))

    out = os.path.join(OUT_DIR, f"meteogram{i}.bmp")
    pal = canvas.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    pal.save(out, format="BMP")                   # uncompressed 8-bit palette BMP, ~77 KB
    old_png = os.path.join(OUT_DIR, f"meteogram{i}.png")
    if os.path.exists(old_png):
        os.remove(old_png)                        # the old PNG format is no longer used
    print(f"{out}: {os.path.getsize(out)} bytes | full render {fw}x{fh}, "
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
