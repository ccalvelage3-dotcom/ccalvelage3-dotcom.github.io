# calvelage.github.io

Personal website of Christopher M. Calvelage. A small static site: content lives in YAML files,
`build.py` renders it with Jinja2 into `_site/`, and a GitHub Actions workflow publishes `_site/`
to GitHub Pages on every push to `main`.

## Edit content

| What | File |
|---|---|
| Name, role, bio, links, "Recent" list, headshot | `_data/profile.yml` |
| Research themes (each is a panel on the home page) and project cards | `_data/research.yml` |
| Software cards | `_data/software.yml` |
| Publications | `_data/publications.yml` |
| CV page | `_data/cv.yml` |
| Layout | `templates/*.html` |
| Styling | `assets/css/style.css` |

You can edit these files directly on github.com; the site rebuilds automatically.

## Preview locally

```bash
pip install -r requirements.txt
python build.py --serve        # http://localhost:8000
```

## Add a figure

```bash
python tools/add_figure.py path/to/figure.png assets/img/research/my-figure.png --crop x0,y0,x1,y1
```

Cropping is in source pixels; output is resized to 1400 px wide. Use a `.jpg` destination for
shaded relief, photos, or smooth color maps. Then set `image:` and `image_alt:` on the card in
`_data/research.yml`.

## Flow-model figures

The Rasuwa–Trishuli card shows the last time step of its r.avaflow simulation, and the Budhi
Gandaki card shows its run 5 minutes in. `tools/make_flow_anim.py` renders a run as flow height over
shaded relief; it writes an animated `NAME.webp` and a still `NAME-still.jpg` (`--still last` for
the final frame, `--still-time SECONDS` for a given time). The site uses the still, renamed
(needs numpy and Pillow):

```bash
# r.avaflow ASCII output
python tools/make_flow_anim.py ascii path/to/exresults/exascii rasuwa-flow --dt 10 --still last
# condensed results.npz + inputs.npz
python tools/make_flow_anim.py npz results.npz inputs.npz budhi-flow --step 2 --tmax 600 --aspect 0.72 --pad 1000 --still-time 300
```

Cards can also show an animation instead (`animation:`, `still:`, `loop_ms:` in
`_data/research.yml`); the page then adds a pause/replay button and respects reduced-motion
settings. `fig_ratio: 1 / 1` gives a tall figure a square box.

## Link-preview image

`assets/img/og-card.jpg` (1200×630) is what LinkedIn, Slack, and email show when the site is
shared. It's a snapshot of the header; regenerate it if the name, title, or photo changes.

## Header waveform and waterfall

The header shows the M8.8 Kamchatka earthquake (29 July 2025) as recorded on the EPIC fiber-optic
cable. The line is the average of 279 DAS channels, band-passed 0.01–0.2 Hz
(`_data/hero_wave.yml`). The background behind the name is a waterfall of the same record, one row
per channel over the same time window, so its arrivals line up with the line below
(`assets/img/hero-waterfall.jpg`). To regenerate both from another record (needs numpy, scipy,
and Pillow):

```bash
python tools/make_hero_wave.py path/to/lowrate_record.npz
```

Then edit `CAPTION` in that script or the `caption` in `_data/hero_wave.yml`.

## Check for new publications

Google Scholar has no API, so new papers are found through ORCID and OpenAlex:

```bash
python tools/check_new_pubs.py
```

It prints YAML stubs for DOIs not yet listed. Conference abstracts without DOIs still need to be
added by hand from the Scholar profile.
