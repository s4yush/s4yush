"""Builds two extra cards with the same look as the other profile SVGs.

  assets/clock.svg     IST time and date as of this workflow run
  assets/snapshot.svg  followers, following, repositories, stars, member since

No server and no Cloudflare. Both files are plain SVGs written by the workflow.

An SVG shown in a README cannot run code, so the clock cannot tick live and
nobody can count visits. The clock shows the time of the last workflow run,
and the card says so. Run: python3 scripts/extra_assets.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone

import build_assets as ba
import config

IST = timezone(timedelta(hours=5, minutes=30))


def render_clock(now_utc: datetime) -> str:
    now = now_utc.astimezone(IST)
    hour12 = now.hour % 12 or 12
    clock = f"{hour12:02d}:{now.minute:02d}"
    period = "AM" if now.hour < 12 else "PM"
    canvas = ba.Canvas(ba.CARD_WIDTH, 190, f"India time at last refresh: {clock} {period}, {now:%A}")
    ba.frame(canvas, "Clock", "IST \u00b7 India Standard Time")
    canvas.add(
        ba.el(
            "g",
            ba.text(clock, ba.CARD_PAD, 138, 76, ba.Color.TEXT, 800),
            ba.text(period, ba.CARD_PAD + 214, 138, 28, ba.Color.BLUE, 700),
            ba.text(now.strftime("%A"), ba.CARD_WIDTH - ba.CARD_PAD, 110, 28, ba.Color.TEXT, 700, "end"),
            ba.text(f"{now.day} {now:%B %Y}", ba.CARD_WIDTH - ba.CARD_PAD, 138, 18, ba.Color.MUTED, 500, "end"),
            ba.text("As of the last profile refresh", ba.CARD_WIDTH - ba.CARD_PAD, 164, 13, ba.Color.MUTED, 400, "end"),
            class_="rise",
        )
    )
    return canvas.render()


def render_snapshot(profile: ba.Profile) -> str:
    tiles = (
        ("Followers", ba.human(profile.followers), ba.Color.BLUE),
        ("Following", ba.human(profile.following), ba.Color.PURPLE),
        ("Repositories", ba.human(profile.repo_count), ba.Color.GREEN),
        ("Stars", ba.human(profile.stars), ba.Color.YELLOW),
        ("On GitHub since", str(profile.created.year), ba.Color.ORANGE),
    )
    gap, tile_h, top = 14, 92, 84
    tile_w = (ba.INNER_WIDTH - gap * (len(tiles) - 1)) / len(tiles)
    canvas = ba.Canvas(ba.CARD_WIDTH, top + tile_h + ba.CARD_PAD, f"GitHub snapshot for {profile.login}")
    ba.frame(canvas, "Snapshot", f"@{profile.login}")
    for index, (label, value, color) in enumerate(tiles):
        x = ba.CARD_PAD + index * (tile_w + gap)
        canvas.add(
            ba.el(
                "g",
                ba.el("rect", x=x, y=top, width=tile_w, height=tile_h, rx=14, fill=ba.Color.PANEL, fill_opacity=0.9, stroke=ba.Color.BORDER),
                ba.el("rect", x=x + 16, y=top + 16, width=28, height=4, rx=2, fill=color),
                ba.text(value, x + 16, top + 58, 32, color, 800),
                ba.text(label, x + 16, top + 80, 13, ba.Color.MUTED, 500),
                class_="rise",
                style=f"animation-delay:{index * 0.06:.2f}s",
            )
        )
    return canvas.render()


def main() -> int:
    failures: list[str] = []
    assets: dict[str, str | None] = {
        "clock.svg": ba.guarded("clock.svg", lambda: render_clock(datetime.now(timezone.utc)), failures),
    }
    if config.GITHUB.configured:
        try:
            profile = ba.fetch_profile(ba.GitHubClient(config.GITHUB.token), config.GITHUB.login)
            assets["snapshot.svg"] = ba.guarded("snapshot.svg", lambda: render_snapshot(profile), failures)
        except ba.GitHubError as error:
            failures.append(f"snapshot.svg: GitHub API error: {error}")
    else:
        failures.append("snapshot.svg: GITHUB_TOKEN and PROFILE_LOGIN are not set")
    ba.write_assets(assets, ba.ASSETS_DIR)
    for failure in failures:
        print(f"FAILED {failure}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
