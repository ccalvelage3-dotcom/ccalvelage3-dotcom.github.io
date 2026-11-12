#!/usr/bin/env python3
"""Render an r.avaflow simulation as a looping animation for a research card.

Two kinds of run directory are supported:

  # r.avaflow ASCII output (…/exresults/exascii with exhflowNNNN.asc and exelev.asc)
  python tools/make_flow_anim.py ascii RUN_ASCII_DIR NAME --dt 10

  # condensed run (results.npz with hflow[t, y, x] and t_frames; inputs.npz with elev, x, y)
  python tools/make_flow_anim.py npz RESULTS.npz INPUTS.npz NAME

Writes assets/img/research/NAME.webp (animated) and NAME-still.jpg (the last frame, shown to
visitors who prefer reduced motion). Flow height is drawn in the site's purples over gray shaded
relief, cropped to the area the flow reaches. Needs numpy and Pillow.
"""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "img" / "research"
FONT = "/System/Library/Fonts/Helvetica.ttc"

# flow height (m, log scale 1–100) -> light lavender to deep purple
STOPS = [(0.0, (214, 196, 240)), (0.35, (160, 116, 214)), (0.7, (98, 54, 160)), (1.0, (52, 22, 92))]


def read_asc(path):
    with open(path) as f:
        head = {}
        for _ in range(6):
            k, v = f.readline().split()
            head[k.lower()] = float(v)
        a = np.loadtxt(f, dtype=np.float32)
    a[a == head.get("nodata_value", -9999)] = 0
    return a, head["cellsize"]


def hillshade(z, dx, az=315.0, alt=45.0):
    gy, gx = np.gradient(z, dx)
    slope = np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gx, gy)
    a, e = np.radians(360 - az + 90), np.radians(alt)
    hs = np.sin(e) * np.cos(slope) + np.cos(e) * np.sin(slope) * np.cos(a - aspect)
    return np.clip(hs, 0, 1)


def colorize(h):
    v = np.clip(np.log10(np.clip(h, 1, 100)) / 2, 0, 1)
    xs = [s[0] for s in STOPS]
    cols = np.array([s[1] for s in STOPS], float)
    return np.stack([np.interp(v, xs, cols[:, k]) for k in range(3)], axis=-1)


def crop_box(hmax, pad, aspect=1.6):
    rows, cols = np.where(hmax > 0.5)
    r0, r1 = max(rows.min() - pad, 0), min(rows.max() + pad, hmax.shape[0])
    c0, c1 = max(cols.min() - pad, 0), min(cols.max() + pad, hmax.shape[1])
    # widen (or heighten) toward the card's aspect ratio where the grid allows
    h, w = r1 - r0, c1 - c0
    if w / h < aspect:
        grow = int(min(h * aspect - w, hmax.shape[1] - w)) // 2
        c0, c1 = max(c0 - grow, 0), min(c1 + grow, hmax.shape[1])
    else:
        grow = int(min(w / aspect - h, hmax.shape[0] - h)) // 2
        r0, r1 = max(r0 - grow, 0), min(r1 + grow, hmax.shape[0])
    return r0, r1, c0, c1


def render(elev, frames, times, dx, name, width=760, ms=90, hold=14, aspect=1.6, pad_m=1500.0,
           still="last", loops=3, still_time=None):
    hmax = np.max(frames, axis=0)
    r0, r1, c0, c1 = crop_box(hmax, pad=int(pad_m / dx), aspect=aspect)
    hs = hillshade(elev, dx)[r0:r1, c0:c1]
    base = (0.50 + 0.45 * hs)[..., None] * np.array([236, 233, 242])      # faintly violet relief
    scale = min(width / (c1 - c0), width / (r1 - r0))
    size = (int(round((c1 - c0) * scale)), int(round((r1 - r0) * scale)))
    font = ImageFont.truetype(FONT, 34)
    small = ImageFont.truetype(FONT, 22)
    bar_px = 2000 / dx * scale                                             # 2 km scale bar

    out = []
    for h, t in zip(frames, times):
        h = h[r0:r1, c0:c1]
        wet = (h > 0.5)[..., None]
        rgb = np.where(wet, 0.12 * base + 0.88 * colorize(h), base).astype(np.uint8)
        im = Image.fromarray(rgb).resize(size, Image.LANCZOS)
        d = ImageDraw.Draw(im)
        label = f"{int(t // 60)}:{int(t % 60):02d}"
        d.rounded_rectangle((12, 12, 132, 62), 9, fill=(36, 19, 61))
        d.text((26, 18), label, font=font, fill=(243, 238, 251))
        x1, y1 = size[0] - 18, size[1] - 22
        d.rectangle((x1 - bar_px, y1, x1, y1 + 5), fill=(36, 19, 61))
        d.text((x1 - bar_px, y1 - 28), "2 km", font=small, fill=(36, 19, 61))
        out.append(im)

    durations = [ms] * (len(out) - 1) + [ms * hold]
    anim = OUT / f"{name}.webp"
    out[0].save(anim, save_all=True, append_images=out[1:], duration=durations, loop=loops,
                quality=72, method=6)
    if still_time is not None:
        k = int(np.argmin(np.abs(np.asarray(times) - still_time)))
    else:
        k = len(out) - 1 if still == "last" else int(((frames > 0.5).sum(axis=(1, 2))).argmax())
    still = OUT / f"{name}-still.jpg"
    out[k].save(still, quality=85, optimize=True, progressive=True)
    print(f"{anim.relative_to(ROOT)}  {size[0]}x{size[1]}  {len(out)} frames  "
          f"{anim.stat().st_size // 1024} KB;  {still.name} {still.stat().st_size // 1024} KB")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="kind", required=True)
    a = sub.add_parser("ascii")
    a.add_argument("dir"); a.add_argument("name")
    a.add_argument("--dt", type=float, default=10.0, help="seconds between frames")
    a.add_argument("--tmax", type=float, default=None)
    n = sub.add_parser("npz")
    n.add_argument("results"); n.add_argument("inputs"); n.add_argument("name")
    n.add_argument("--step", type=int, default=2, help="use every Nth frame")
    n.add_argument("--tmax", type=float, default=None)
    for p_ in (a, n):
        p_.add_argument("--aspect", type=float, default=1.6, help="target width/height of the crop")
        p_.add_argument("--pad", type=float, default=1500.0, help="margin around the flow, m")
        p_.add_argument("--still", choices=["last", "maxarea"], default="last")
        p_.add_argument("--loops", type=int, default=3, help="times to play; 0 = forever")
        p_.add_argument("--still-time", type=float, default=None, help="seconds: use this frame as the still")
    args = ap.parse_args()

    if args.kind == "ascii":
        d = Path(args.dir)
        elev, dx = read_asc(d / "exelev.asc")
        paths = sorted(d.glob("exhflow[0-9][0-9][0-9][0-9].asc"))
        times = np.arange(len(paths)) * args.dt
        if args.tmax is not None:
            paths = [p for p, t in zip(paths, times) if t <= args.tmax]
            times = times[: len(paths)]
        frames = np.stack([read_asc(p)[0] for p in paths])
    else:
        r = np.load(args.results, allow_pickle=False)
        i = np.load(args.inputs, allow_pickle=False)
        frames, times = r["hflow"].astype(np.float32), r["t_frames"]
        elev = i["elev"].astype(np.float32)
        dx = float(abs(i["x"][1] - i["x"][0]))
        if i["y"][1] > i["y"][0]:            # rows run south -> north: flip to north-up
            frames, elev = frames[:, ::-1], elev[::-1]
        keep = slice(None, None, args.step)
        frames, times = frames[keep], times[keep]
        if args.tmax is not None:
            m = times <= args.tmax
            frames, times = frames[m], times[m]
    render(elev, frames, times, dx, args.name, aspect=args.aspect, pad_m=args.pad, still=args.still, loops=args.loops, still_time=args.still_time)


if __name__ == "__main__":
    main()
