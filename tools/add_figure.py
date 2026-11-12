#!/usr/bin/env python3
"""Copy a figure into the site, optionally cropping and resizing it for the web.

    python tools/add_figure.py SRC assets/img/research/NAME.png [--crop x0,y0,x1,y1] [--width 1400]

--crop takes pixel coordinates in the source image. PDFs are rasterized (page 1) with pdftoppm.
Output is PNG for line art, or JPEG if DEST ends in .jpg.
"""
import argparse
import subprocess
import tempfile
from pathlib import Path

from PIL import Image


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dest")
    ap.add_argument("--crop", help="x0,y0,x1,y1 in source pixels")
    ap.add_argument("--width", type=int, default=1400, help="max output width in px")
    ap.add_argument("--page", type=int, default=1, help="PDF page to rasterize")
    a = ap.parse_args()

    src = Path(a.src)
    if src.suffix.lower() == ".pdf":
        tmp = Path(tempfile.mkdtemp()) / "page"
        subprocess.run(["pdftoppm", "-png", "-r", "200", "-f", str(a.page), "-l", str(a.page),
                        "-singlefile", str(src), str(tmp)], check=True)
        src = tmp.with_suffix(".png")

    im = Image.open(src)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, "white")
        im = Image.alpha_composite(bg, im).convert("RGB")
    else:
        im = im.convert("RGB")
    if a.crop:
        im = im.crop(tuple(int(v) for v in a.crop.split(",")))
    if im.width > a.width:
        im = im.resize((a.width, round(im.height * a.width / im.width)), Image.LANCZOS)

    dest = Path(a.dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.suffix.lower() in (".jpg", ".jpeg"):
        im.save(dest, quality=84, optimize=True, progressive=True)
    else:
        im = im.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) \
            if a.width <= 1600 else im
        im.save(dest, optimize=True)
    print(f"{dest}  {im.width}x{im.height}  {dest.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
