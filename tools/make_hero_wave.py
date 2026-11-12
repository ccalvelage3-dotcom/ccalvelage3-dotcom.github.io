#!/usr/bin/env python3
"""Build the home-page header graphics from a DAS record.

    python tools/make_hero_wave.py /path/to/m88_20250729.npz

Reads a low-rate DAS strain array (keys: strain [time, channel], fs) and writes:

  _data/hero_wave.yml               the line across the header: all usable channels band-passed,
                                    RMS-normalized, polarity-aligned, and averaged; min/max
                                    decimated to ~1,400 points and scaled to [-1, 1]
  assets/img/hero-waterfall.jpg     the background above it: one row per channel, over exactly
                                    the same time window, in the site's purple/green palette

Needs numpy, scipy, and Pillow locally; the site build only reads the outputs.
"""
import argparse
from pathlib import Path

import numpy as np
import yaml
from PIL import Image
from scipy.ndimage import uniform_filter1d
from scipy.signal import butter, detrend, sosfiltfilt

ROOT = Path(__file__).resolve().parents[1]
CAPTION = ("M8.8 Kamchatka earthquake, 29 July 2025, recorded as strain on the fiber-optic cable at "
           "the EarthScope Primary Instrument Center, Socorro, New Mexico. Background: each row is "
           "one channel along the cable. Line: the average of all channels.")
EDGE_S = 60            # trimmed from both ends to drop filter edge effects
PRE_EVENT_S = 600      # quiet window before the P wave, used to rank channels by signal-to-noise

# diverging palette centered on the header background, so quiet ground disappears into it
STOPS = [(-1.0, (150, 108, 218)), (-0.5, (78, 44, 128)), (0.0, (36, 19, 61)),
         (0.5, (30, 92, 62)), (1.0, (127, 207, 159))]


def bandpass(x, fs, lo, hi):
    return sosfiltfilt(butter(4, [lo, hi], btype="band", fs=fs, output="sos"), x, axis=0)


def trace(x, fs, bins):
    y = bandpass(x, fs, 0.01, 0.2)
    rms = np.sqrt((y ** 2).mean(axis=0))
    med = np.median(rms)
    y = y[:, (rms > 0.3 * med) & (rms < 3 * med)]
    y /= np.sqrt((y ** 2).mean(axis=0))
    y *= np.sign((y * np.median(y, axis=1)[:, None]).sum(axis=0))
    stack = y.mean(axis=1)[int(EDGE_S * fs):-int(EDGE_S * fs)]
    out = []
    for chunk in np.array_split(stack, bins):
        i, j = int(chunk.argmin()), int(chunk.argmax())
        out += [chunk[min(i, j)], chunk[max(i, j)]]
    out = np.asarray(out) / np.abs(out).max()
    return out, y.shape[1]


def waterfall(x, fs, width=1800, height=420):
    y = bandpass(x, fs, 0.01, 0.1)[int(EDGE_S * fs):-int(EDGE_S * fs)]
    noise = np.sqrt((y[: int(PRE_EVENT_S * fs)] ** 2).mean(axis=0))
    sig = np.sqrt((y ** 2).mean(axis=0))
    snr = sig / noise
    keep = snr > np.percentile(snr, 30)
    y = uniform_filter1d(y[:, keep] / sig[keep], 5, axis=1)
    edges = np.linspace(0, y.shape[0], width + 1).astype(int)
    img = np.stack([y[a:b].mean(axis=0) for a, b in zip(edges[:-1], edges[1:])], axis=1)
    img = img[np.linspace(0, img.shape[0] - 1, height).round().astype(int)]
    v = np.clip(img / 2.6, -1, 1)
    v = np.sign(v) * np.abs(v) ** 0.8
    xs = [s[0] for s in STOPS]
    cols = np.array([s[1] for s in STOPS], float)
    rgb = np.stack([np.interp(v, xs, cols[:, k]) for k in range(3)], axis=-1).astype(np.uint8)
    return Image.fromarray(rgb), int(keep.sum())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("npz")
    ap.add_argument("--bins", type=int, default=700, help="trace has 2 x bins points")
    a = ap.parse_args()

    d = np.load(a.npz, allow_pickle=False)
    fs = float(d["fs"])
    x = d["strain"]
    x = detrend(x[:, np.isfinite(x).all(axis=0)], axis=0)

    values, n_trace = trace(x, fs, a.bins)
    (ROOT / "_data" / "hero_wave.yml").write_text(yaml.safe_dump({
        "caption": CAPTION,
        "source": f"{Path(a.npz).name}; line: {n_trace} channels, 0.01-0.2 Hz",
        "background": "assets/img/hero-waterfall.jpg",
        "values": [round(float(v), 3) for v in values],
    }, width=100, sort_keys=False))

    img, n_fall = waterfall(x, fs)
    dest = ROOT / "assets" / "img" / "hero-waterfall.jpg"
    img.save(dest, quality=82, optimize=True, progressive=True)
    print(f"line: {n_trace} channels -> _data/hero_wave.yml; "
          f"waterfall: {n_fall} channels -> {dest.relative_to(ROOT)} ({dest.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
