#!/usr/bin/env python3
"""Build the static site from _data/*.yml + templates/ into _site/.

    python build.py            # build once
    python build.py --serve    # build, then serve at http://localhost:8000

Requires: pyyaml, jinja2 (pip install -r requirements.txt).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import html
import math
import random
import re
import shutil
import sys
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "_data"
OUT = ROOT / "_site"
OWNER_SURNAME = "Calvelage"

STATUS_LABELS = {
    "published": "Published",
    "preprint": "Preprint · in review",
    "in-review": "In review",
    "submitted": "Submitted",
    "in-prep": "Manuscript in preparation",
    "active": "Research in progress",
    "report": "Rapid response",
}

# (template, output file, path used in canonical URLs and the sitemap; None = not in sitemap)
PAGES = [
    ("index.html", "index.html", ""),
    ("research.html", "research.html", "research.html"),
    ("cv.html", "cv.html", "cv.html"),
    ("404.html", "404.html", None),
]


def load(name: str):
    path = DATA / f"{name}.yml"
    return yaml.safe_load(path.read_text()) if path.exists() else {}


def highlight_owner(authors: str) -> Markup:
    """Escape an author string and bold the site owner's name."""
    safe = html.escape(" ".join(authors.split()))
    pattern = rf"{OWNER_SURNAME},\s*[A-Z]\.(?:\s*[A-Z]\.)*"
    return Markup(re.sub(pattern, lambda m: f"<strong>{m.group(0)}</strong>", safe))


def wave_path(values, width=1200, height=120, pad=4) -> str:
    """SVG path for a trace already scaled to [-1, 1] (see tools/make_hero_wave.py)."""
    mid, amp = height / 2, height / 2 - pad
    step = width / (len(values) - 1)
    return "M" + " L".join(f"{i * step:.1f},{mid - v * amp:.1f}" for i, v in enumerate(values))


def seismogram_path(width=1200, height=120, seed=7) -> str:
    """Fallback: a deterministic, synthetic three-phase seismogram (noise, P, S, coda)."""
    rng = random.Random(seed)
    mid = height / 2
    pts = []
    p_on, s_on = 0.30, 0.47
    for i in range(width // 2 + 1):
        x = i * 2
        t = x / width
        amp = 2.2  # background noise
        if t > p_on:
            amp += 15 * math.exp(-(t - p_on) * 22)
        if t > s_on:
            amp += 44 * math.exp(-(t - s_on) * 9) * (1 - math.exp(-(t - s_on) * 160))
        freq = 0.55 if t > s_on else 0.9
        y = mid + amp * (0.65 * math.sin(i * freq + rng.uniform(-0.6, 0.6)) + rng.uniform(-0.45, 0.45))
        pts.append(f"{x},{y:.1f}")
    return "M" + " L".join(pts)


def versioned(rel: str) -> str:
    """Append a short content hash to a local asset path (`{{ path | v }}`), so browsers fetch the
    file again whenever it changes instead of showing a cached copy."""
    if not rel or "://" in rel:
        return rel
    f = ROOT / rel.split("?")[0].split("#")[0]
    if not f.is_file():
        return rel
    return f"{rel}?v={hashlib.sha1(f.read_bytes()).hexdigest()[:8]}"


def build() -> None:
    profile = load("profile")
    research = load("research")
    software = load("software")
    pubs = load("publications")
    cv = load("cv")
    hero = load("hero_wave")

    # tag every project with its theme, and resolve each theme's home-page figure and highlights
    n_projects = 0
    for t in research.get("themes", []):
        projects = {p["id"]: p for p in t.get("projects", [])}
        for p in projects.values():
            p["theme_id"], p["theme_title"] = t["id"], t["title"]
        n_projects += len(projects)
        t["n"] = len(projects)

        def pick(pid, t=t, projects=projects):
            if pid not in projects:
                sys.exit(f"research.yml: theme {t['id']!r} names project {pid!r}, which isn't in that theme")
            return projects[pid]

        t["figure_project"] = pick(t["figure"]) if t.get("figure") else None
        t["highlight_projects"] = [pick(pid) for pid in t.get("highlights", [])]

    items = sorted(pubs.get("items", []), key=lambda p: -int(p.get("year", 0)))
    groups = [
        ("article", "Peer-reviewed articles"),
        ("preprint", "Preprints & manuscripts in review"),
        ("dataset", "Datasets"),
        ("thesis", "Theses"),
        ("abstract", "Conference abstracts"),
    ]
    pub_groups = [
        {"key": k, "title": t, "items": [p for p in items if p.get("type") == k]}
        for k, t in groups
    ]
    pub_groups = [g for g in pub_groups if g["items"]]

    user, domain = profile["email"].split("@")
    site_url = profile.get("site_url", "").rstrip("/")

    env = Environment(
        loader=FileSystemLoader(ROOT / "templates"),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["authors"] = highlight_owner
    env.filters["safe_html"] = lambda s: Markup(s or "")
    env.filters["v"] = versioned
    env.globals.update(
        profile=profile,
        site_url=site_url,
        email_user=user,
        email_domain=domain,
        status_labels=STATUS_LABELS,
        year=dt.date.today().year,
        updated=dt.date.today().strftime("%B %Y"),
        wave=wave_path(hero["values"]) if hero.get("values") else seismogram_path(),
        wave_caption=hero.get("caption", ""),
        wave_bg=hero.get("background", ""),
    )

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(ROOT / "assets", OUT / "assets")
    (OUT / ".nojekyll").touch()

    ctx = dict(research=research, software=software, pub_groups=pub_groups, cv=cv,
               n_projects=n_projects)
    for template, out_name, url_path in PAGES:
        page_url = f"{site_url}/{url_path}" if url_path is not None else site_url + "/"
        (OUT / out_name).write_text(
            env.get_template(template).render(page=out_name, page_url=page_url, **ctx))

    today = dt.date.today().isoformat()
    urls = "".join(f"  <url><loc>{site_url}/{u}</loc><lastmod>{today}</lastmod></url>\n"
                   for _, _, u in PAGES if u is not None)
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + "</urlset>\n")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {site_url}/sitemap.xml\n")
    print(f"Built {len(PAGES)} pages ({n_projects} projects in {len(research['themes'])} themes) "
          f"into {OUT.relative_to(ROOT)}/")


def serve(port: int = 8000) -> None:
    import functools
    import http.server

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(OUT))
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), handler) as httpd:
        print(f"Serving at http://localhost:{port}  (Ctrl-C to stop)")
        httpd.serve_forever()


if __name__ == "__main__":
    build()
    if "--serve" in sys.argv:
        serve()
