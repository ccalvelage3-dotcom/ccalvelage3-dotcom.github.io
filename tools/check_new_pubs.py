#!/usr/bin/env python3
"""List works on ORCID / OpenAlex that are not yet in _data/publications.yml.

    python tools/check_new_pubs.py

Google Scholar has no API, so this checks the two open sources that track the same papers.
It prints YAML stubs for anything new; review them and paste the real ones into publications.yml.
DOIs under `exclude:` in publications.yml are skipped.
"""
import json
import urllib.request
from pathlib import Path

import yaml

ORCID = "0009-0005-9807-4255"
ROOT = Path(__file__).resolve().parents[1]


def get(url: str):
    req = urllib.request.Request(url, headers={"Accept": "application/json",
                                               "User-Agent": "personal-site-pubcheck"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main() -> None:
    data = yaml.safe_load((ROOT / "_data" / "publications.yml").read_text())
    known = {str(p.get("doi", "")).lower() for p in data["items"] if p.get("doi")}
    known |= {str(d).lower() for d in data.get("exclude", [])}

    found = {}
    for g in get(f"https://pub.orcid.org/v3.0/{ORCID}/works").get("group", []):
        s = g["work-summary"][0]
        ids = {e["external-id-type"]: e["external-id-value"]
               for e in s.get("external-ids", {}).get("external-id", [])}
        if "doi" in ids:
            year = ((s.get("publication-date") or {}).get("year") or {}).get("value")
            found[ids["doi"].lower()] = (year, s["title"]["title"]["value"], "ORCID")

    oa = get(f"https://api.openalex.org/works?filter=author.orcid:{ORCID}&per-page=100"
             "&select=doi,title,publication_year,primary_location")
    for w in oa.get("results", []):
        if w.get("doi"):
            doi = w["doi"].replace("https://doi.org/", "").lower()
            found.setdefault(doi, (w.get("publication_year"), w.get("title"), "OpenAlex"))

    # skip peer-review history records (e.g. "Author response for ...")
    new = {d: v for d, v in found.items()
           if d not in known and "/response" not in d and "/review" not in d
           and not str(v[1]).lower().startswith(("author response", "review for", "decision letter"))}
    if not new:
        print("No new DOI-bearing works found.")
        return
    print(f"# {len(new)} work(s) not in publications.yml. Review before adding:\n")
    for doi, (year, title, src) in sorted(new.items(), key=lambda kv: str(kv[1][0]), reverse=True):
        print(f"  - type: article   # from {src}; check type, authors, venue\n"
              f"    year: {year}\n    title: >-\n      {title}\n"
              f"    authors: TODO\n    venue: TODO\n    doi: {doi}\n")


if __name__ == "__main__":
    main()
