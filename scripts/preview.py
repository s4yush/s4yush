"""Offline preview: build every asset from synthetic data (no tokens, no network).

Usage: python3 scripts/preview.py [output_dir]
Writes SVGs to ./preview by default and validates that each one is well-formed XML.
"""
from __future__ import annotations

import random
import sys
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_assets as b  # noqa: E402


def mock_profile(today: date) -> b.Profile:
    rng = random.Random(7)
    start = today - timedelta(days=370)
    days = tuple(
        b.Day(start + timedelta(days=i), 0 if rng.random() < 0.35 else rng.randint(1, 12))
        for i in range(371)
    )
    repos = tuple(
        b.Repo(f"project-{i}", f"Demo repository number {i}", f"https://github.com/s4yush/project-{i}",
               rng.randint(0, 40), rng.randint(0, 9), lang, color)
        for i, (lang, color) in enumerate([("Python", "#3572A5"), ("C", "#555555"), ("JavaScript", "#f1e05a")])
    )
    now = datetime.now(timezone.utc)
    log = tuple(
        b.Commit(f"project-{i % 3}", f"feat: change {i}", now - timedelta(hours=i * 7 + 1),
                 rng.randint(5, 300), rng.randint(0, 120), rng.randint(1, 9))
        for i in range(12)
    )
    return b.Profile(
        login="s4yush", created=date(2023, 6, 1), followers=12, repo_count=9, repos=repos,
        languages=(b.Language("Python", 90000, "#3572A5"), b.Language("C", 40000, "#555555"),
                   b.Language("JavaScript", 20000, "#f1e05a")),
        days=days, commits=sum(d.count for d in days), pull_requests=14, issues=5, reviews=3,
        today=today, name="Suyash Singh", following=20, gists=2, orgs=1, starred=30,
        contributed_to=4, merged_prs=9, commit_log=log,
    )


def mock_music(now: datetime) -> b.Music:
    tracks = tuple(b.Track(f"Track {i}", f"Artist {i}", plays=50 - i * 7) for i in range(5))
    artists = tuple(b.Artist(f"Artist {i}", plays=90 - i * 10, tags=("indie",)) for i in range(5))
    return b.Music("Preview", "last 30 days", b.Track("Now Song", "Now Artist", playing=True),
                   tracks, artists, (("indie", 40), ("rock", 30), ("pop", 20)),
                   (("Plays", "1,234"), ("Artists", "88")))


def mock_waka() -> b.Waka:
    rows = (("Python", 62.0, "#3572A5"), ("C", 25.0, "#555555"), ("Other", 13.0, "#8b949e"))
    return b.Waka("12 hrs 30 mins", "1 hr 47 mins", "310 hrs", "Sat", rows, rows, rows)


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("preview")
    now = datetime.now(timezone.utc)
    assets, failures = b.build_assets(mock_profile(now.date()), b.IDENTITY, mock_music(now), mock_waka(), now)
    b.write_assets(assets, out)
    bad = []
    for name, content in assets.items():
        if content is None:
            continue
        try:
            ET.fromstring(content)
        except ET.ParseError as error:
            bad.append(f"{name}: {error}")
    for line in failures + bad:
        print("FAILED", line, file=sys.stderr)
    return 1 if failures or bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
