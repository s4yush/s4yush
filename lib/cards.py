from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, TypeVar

import build_assets as ba
import config
import extra_cards as extra

T = TypeVar("T")

STATIC = "public, max-age=0, s-maxage=3600, stale-while-revalidate=86400"
GITHUB = "public, max-age=0, s-maxage=600, stale-while-revalidate=86400"
LIVE = "public, max-age=0, s-maxage=60, stale-while-revalidate=600"
CLOCK = "public, max-age=0, s-maxage=20, stale-while-revalidate=20"
VIEWS = "public, max-age=0, s-maxage=30, stale-while-revalidate=30"

STORE: dict[str, tuple[float, object]] = {}


def remembered(key: str, ttl: float, load: Callable[[], T | None]) -> T | None:
    entry = STORE.get(key)
    now = time.monotonic()
    if entry and now - entry[0] < ttl:
        return entry[1]
    try:
        value = load()
    except Exception:
        if entry:
            return entry[1]
        raise
    if value is None:
        return entry[1] if entry else None
    STORE[key] = (now, value)
    return value


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def profile() -> ba.Profile:
    if not config.GITHUB.configured:
        raise RuntimeError("GITHUB_TOKEN is not set")
    return remembered(
        "profile",
        600,
        lambda: ba.fetch_profile(ba.GitHubClient(config.GITHUB.token), config.GITHUB.login),
    )


def identity() -> ba.Identity:
    return remembered("identity", 3600, ba.load_identity)


def music() -> ba.Music | None:
    return remembered("music", 60, ba.load_music)


def waka() -> ba.Waka | None:
    today = (utc_now() + timedelta(hours=ba.UTC_OFFSET_HOURS)).date()
    return remembered("waka", 120, lambda: ba.load_waka(today))


def render_music() -> str | None:
    data = music()
    return None if data is None else ba.render_music(data, utc_now())


def render_wakatime() -> str | None:
    data = waka()
    return None if data is None else ba.render_wakatime(data)


def render_views() -> str:
    return extra.render_views(extra.fetch_count(config.GITHUB.login), config.GITHUB.login)


@dataclass(frozen=True)
class Card:
    title: str
    cache: str
    render: Callable[[], str | None]


REGISTRY: dict[str, Card] = {
    "header": Card("Header", STATIC, lambda: ba.render_header(identity())),
    "typing": Card("Typing", STATIC, lambda: ba.render_typing(identity())),
    "about": Card("About", STATIC, lambda: ba.render_about(identity())),
    "skills": Card("Skills", STATIC, lambda: ba.render_skills(identity())),
    "timeline": Card("Timeline", STATIC, lambda: ba.render_timeline(identity())),
    "certificates": Card("Certificates", STATIC, lambda: ba.render_certificates(identity())),
    "divider": Card("Divider", STATIC, ba.render_divider),
    "profile": Card("Profile", GITHUB, lambda: ba.render_profile(profile(), identity())),
    "stats": Card("Stats", GITHUB, lambda: ba.render_stats(profile())),
    "mix": Card("Contribution mix", GITHUB, lambda: ba.render_mix(profile())),
    "achievements": Card("Achievements", GITHUB, lambda: ba.render_achievements(profile())),
    "streak": Card("Streak", GITHUB, lambda: ba.render_streak(profile())),
    "languages": Card("Languages", GITHUB, lambda: ba.render_languages(profile())),
    "codestats": Card("Code stats", GITHUB, lambda: ba.render_codestats(profile(), utc_now())),
    "rhythm": Card("Rhythm", GITHUB, lambda: ba.render_rhythm(profile())),
    "activity": Card("Activity", GITHUB, lambda: ba.render_activity(profile())),
    "projects": Card("Projects", GITHUB, lambda: ba.render_projects(profile())),
    "footer": Card("Footer", GITHUB, lambda: ba.render_footer(identity(), profile().today)),
    "music": Card("Music", LIVE, render_music),
    "wakatime": Card("WakaTime", LIVE, render_wakatime),
    "clock": Card("Clock", CLOCK, lambda: extra.render_clock(utc_now())),
    "views": Card("Views", VIEWS, render_views),
}
