from __future__ import annotations

import json
import math
import os
import random
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from textwrap import shorten, wrap
from typing import Sequence
from xml.sax.saxutils import escape

API_URL = "https://api.github.com/graphql"
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
RETRYABLE = frozenset({"RATE_LIMITED", "SERVICE_UNAVAILABLE", "TIMEOUT"})
MAX_ATTEMPTS = 4
MIN_WEEKS = 16
MAX_WEEKS = 53
CARD_WIDTH = 800
CARD_PAD = 32
INNER_WIDTH = CARD_WIDTH - 2 * CARD_PAD
NBSP = "\u00a0"


class Color:
    BG = "#0d1117"
    BG_SOFT = "#131b2e"
    PANEL = "#161b22"
    BORDER = "#30363d"
    TEXT = "#e6edf3"
    MUTED = "#8b949e"
    BLUE = "#58a6ff"
    CYAN = "#39c5cf"
    PURPLE = "#bc8cff"
    PINK = "#f778ba"
    GREEN = "#3fb950"
    ORANGE = "#ffa657"
    YELLOW = "#e3b341"
    RED = "#ff7b72"
    HEAT = ("#161b22", "#12314f", "#1f6feb", "#8957e5", "#d2a8ff")


@dataclass(frozen=True)
class Identity:
    name: str
    class_name: str
    title: str
    status: str
    taglines: tuple[str, ...]
    role: str
    education: str
    stack: tuple[str, ...]
    currently: str
    next_up: str
    open_to: tuple[str, ...]
    cta_title: str
    cta_text: str


IDENTITY = Identity(
    name="Suyash Singh",
    class_name="Suyash",
    title="Product-minded Developer",
    status="Building and sharing work in public",
    taglines=(
        "B.Tech CSE Student",
        "Python \u2022 C \u2022 Git & GitHub",
        "Learning & Building in Public",
        "More Projects Coming Soon",
    ),
    role="Product-minded developer",
    education="B.Tech CSE",
    stack=("Python", "C", "Git", "GitHub"),
    currently="Learning & building in public",
    next_up="More projects coming soon",
    open_to=("Thoughtful teams", "Ambitious products", "Useful engineering work"),
    cta_title="Let's talk about the next build",
    cta_text="Open to thoughtful teams, ambitious products, and useful engineering work.",
)


@dataclass(frozen=True)
class Day:
    when: date
    count: int


@dataclass(frozen=True)
class Repo:
    name: str
    description: str
    url: str
    stars: int
    forks: int
    language: str
    color: str


@dataclass(frozen=True)
class Language:
    name: str
    size: int
    color: str


@dataclass(frozen=True)
class Streak:
    length: int
    start: date | None
    end: date | None


@dataclass(frozen=True)
class Profile:
    login: str
    created: date
    followers: int
    repo_count: int
    repos: tuple[Repo, ...]
    languages: tuple[Language, ...]
    days: tuple[Day, ...]
    commits: int
    pull_requests: int
    issues: int
    reviews: int
    today: date

    @property
    def stars(self) -> int:
        return sum(repo.stars for repo in self.repos)

    @property
    def contributions(self) -> int:
        return sum(entry.count for entry in self.days)


class GitHubError(RuntimeError):
    pass


class GitHubClient:
    def __init__(self, token: str) -> None:
        self.token = token

    def execute(self, document: str, variables: dict[str, object] | None = None) -> dict:
        body = json.dumps({"query": document, "variables": variables or {}}).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "User-Agent": "profile-assets-builder",
        }
        failure = "unknown failure"
        for attempt in range(1, MAX_ATTEMPTS + 1):
            request = urllib.request.Request(API_URL, data=body, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(request, timeout=45) as response:
                    payload = json.load(response)
            except urllib.error.HTTPError as error:
                failure = f"HTTP {error.code}: {error.read().decode('utf-8', 'replace')[:300]}"
                if error.code < 500 and error.code != 429:
                    raise GitHubError(failure) from error
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
                failure = f"{type(error).__name__}: {error}"
            else:
                errors = payload.get("errors")
                if not errors and payload.get("data") is not None:
                    return payload["data"]
                failure = json.dumps(errors or payload)[:400]
                if errors and not any(item.get("type") in RETRYABLE for item in errors):
                    raise GitHubError(failure)
            if attempt < MAX_ATTEMPTS:
                time.sleep(2**attempt)
        raise GitHubError(failure)


PROFILE_FIELDS = """
login
createdAt
followers { totalCount }
repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false, orderBy: {field: STARGAZERS, direction: DESC}) {
  totalCount
  nodes {
    name
    description
    url
    stargazerCount
    forkCount
    primaryLanguage { name color }
    languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
      edges { size node { name color } }
    }
  }
}
"""

COLLECTION_FIELDS = """
totalCommitContributions
totalIssueContributions
totalPullRequestContributions
totalPullRequestReviewContributions
contributionCalendar { weeks { contributionDays { date contributionCount } } }
"""


def iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def year_windows(created: datetime, now: datetime) -> list[tuple[int, str, str]]:
    windows = []
    for year in range(created.year, now.year + 1):
        start = created if year == created.year else datetime(year, 1, 1, tzinfo=timezone.utc)
        end = now if year == now.year else datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        windows.append((year, iso(start), iso(end)))
    return windows


def collection_selection(year: int, start: str, end: str) -> str:
    return f'y{year}: contributionsCollection(from: "{start}", to: "{end}") {{ {COLLECTION_FIELDS} }}'


def merge_days(collections: Sequence[dict], today: date) -> tuple[Day, ...]:
    merged: dict[date, int] = {}
    for collection in collections:
        for week in collection["contributionCalendar"]["weeks"]:
            for entry in week["contributionDays"]:
                when = date.fromisoformat(entry["date"])
                if when <= today:
                    merged[when] = max(merged.get(when, 0), entry["contributionCount"])
    return tuple(Day(when, merged[when]) for when in sorted(merged))


def parse_repo(node: dict) -> Repo:
    primary = node.get("primaryLanguage") or {}
    return Repo(
        name=node["name"],
        description=(node.get("description") or "").strip(),
        url=node["url"],
        stars=node["stargazerCount"],
        forks=node["forkCount"],
        language=primary.get("name", ""),
        color=primary.get("color") or Color.MUTED,
    )


def aggregate_languages(nodes: Sequence[dict], login: str) -> tuple[Language, ...]:
    sizes: dict[str, int] = {}
    colors: dict[str, str] = {}
    for node in nodes:
        if node["name"].lower() == login.lower():
            continue
        for edge in node["languages"]["edges"]:
            language = edge["node"]
            sizes[language["name"]] = sizes.get(language["name"], 0) + edge["size"]
            colors.setdefault(language["name"], language.get("color") or Color.MUTED)
    ranked = sorted(sizes.items(), key=lambda item: item[1], reverse=True)
    return tuple(Language(name, size, colors[name]) for name, size in ranked)


def parse_profile(user: dict, today: date) -> Profile:
    nodes = user["repositories"]["nodes"]
    collections = [value for key, value in user.items() if key.startswith("y") and key[1:].isdigit()]
    return Profile(
        login=user["login"],
        created=date.fromisoformat(user["createdAt"][:10]),
        followers=user["followers"]["totalCount"],
        repo_count=user["repositories"]["totalCount"],
        repos=tuple(parse_repo(node) for node in nodes),
        languages=aggregate_languages(nodes, user["login"]),
        days=merge_days(collections, today),
        commits=sum(item["totalCommitContributions"] for item in collections),
        pull_requests=sum(item["totalPullRequestContributions"] for item in collections),
        issues=sum(item["totalIssueContributions"] for item in collections),
        reviews=sum(item["totalPullRequestReviewContributions"] for item in collections),
        today=today,
    )


def fetch_profile(client: GitHubClient, login: str, now: datetime | None = None) -> Profile:
    now = now or datetime.now(timezone.utc)
    seed = client.execute("query($login: String!) { user(login: $login) { createdAt } }", {"login": login})
    if seed.get("user") is None:
        raise GitHubError(f"GitHub user '{login}' was not found")
    created = datetime.fromisoformat(seed["user"]["createdAt"].replace("Z", "+00:00"))
    selections = "\n".join(collection_selection(*window) for window in year_windows(created, now))
    document = f"query($login: String!) {{ user(login: $login) {{ {PROFILE_FIELDS} {selections} }} }}"
    return parse_profile(client.execute(document, {"login": login})["user"], now.date())


def week_start(day: date) -> date:
    return day - timedelta(days=(day.weekday() + 1) % 7)


def compute_streaks(days: Sequence[Day], today: date) -> tuple[Streak, Streak]:
    empty = Streak(0, None, None)
    counts = {entry.when: entry.count for entry in days}
    if not counts:
        return empty, empty
    longest = empty
    run = 0
    run_start = cursor = min(counts)
    while cursor <= today:
        if counts.get(cursor, 0) > 0:
            if run == 0:
                run_start = cursor
            run += 1
            if run > longest.length:
                longest = Streak(run, run_start, cursor)
        else:
            run = 0
        cursor += timedelta(days=1)
    anchor = today if counts.get(today, 0) > 0 else today - timedelta(days=1)
    length = 0
    cursor = anchor
    while counts.get(cursor, 0) > 0:
        length += 1
        cursor -= timedelta(days=1)
    current = Streak(length, cursor + timedelta(days=1), anchor) if length else empty
    return current, longest


def activity_window(days: Sequence[Day], today: date) -> tuple[date, int]:
    end_week = week_start(today)
    active = [entry.when for entry in days if entry.count > 0]
    span = (end_week - week_start(min(active))).days // 7 + 3 if active else MIN_WEEKS
    weeks = max(MIN_WEEKS, min(MAX_WEEKS, span))
    return end_week - timedelta(weeks=weeks - 1), weeks


def heat_level(count: int, peak: int) -> int:
    if count <= 0 or peak <= 0:
        return 0
    ratio = count / peak
    return 1 if ratio <= 0.25 else 2 if ratio <= 0.5 else 3 if ratio <= 0.75 else 4


def language_shares(languages: Sequence[Language], limit: int = 6) -> list[tuple[str, float, str]]:
    total = sum(item.size for item in languages)
    if not total:
        return []
    ranked = sorted(languages, key=lambda item: item.size, reverse=True)
    head = ranked if len(ranked) <= limit else ranked[: limit - 1]
    shares = [(item.name, item.size / total * 100, item.color) for item in head]
    rest = ranked[len(head):]
    if rest:
        shares.append(("Other", sum(item.size for item in rest) / total * 100, Color.MUTED))
    return shares


def human(value: int) -> str:
    return f"{value:,}" if value < 100_000 else f"{value / 1000:.0f}k"


def short_date(day: date, today: date) -> str:
    label = f"{day:%b} {day.day}"
    return label if day.year == today.year else f"{label}, {day.year}"


def span_label(streak: Streak, today: date) -> str:
    if not streak.length or streak.start is None or streak.end is None:
        return "No active streak"
    if streak.start == streak.end:
        return short_date(streak.start, today)
    return f"{short_date(streak.start, today)} \u2013 {short_date(streak.end, today)}"


def num(value: float) -> str:
    rendered = f"{value:.2f}".rstrip("0").rstrip(".")
    return "0" if rendered in {"", "-0"} else rendered


def esc(value: object) -> str:
    return escape(str(value), {'"': "&quot;"})


def el(name: str, *children: str, **attributes: object) -> str:
    rendered = []
    for key, value in attributes.items():
        if value is None:
            continue
        content = num(value) if isinstance(value, float) else esc(value)
        rendered.append(f' {key.rstrip("_").replace("_", "-")}="{content}"')
    opening = f"<{name}{''.join(rendered)}"
    inner = "".join(children)
    return f"{opening}>{inner}</{name}>" if inner else f"{opening}/>"


def text(content: str, x: float, y: float, size: float, fill: str, weight: int = 400, anchor: str = "start", **extra: object) -> str:
    return el(
        "text",
        esc(content),
        x=x,
        y=y,
        font_size=size,
        fill=fill,
        font_weight=weight,
        text_anchor=None if anchor == "start" else anchor,
        **extra,
    )


def stop(offset: float, color: str, opacity: float = 1.0) -> str:
    return el("stop", offset=f"{num(offset)}%", stop_color=color, stop_opacity=opacity)


def linear(ident: str, *stops: str, x1: float = 0, y1: float = 0, x2: float = 1, y2: float = 0, **extra: object) -> str:
    return el("linearGradient", *stops, id=ident, x1=x1, y1=y1, x2=x2, y2=y2, **extra)


def radial(ident: str, color: str, opacity: float) -> str:
    return el("radialGradient", stop(0, color, opacity), stop(100, color, 0), id=ident)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def smooth_path(points: Sequence[tuple[float, float]], top: float, bottom: float) -> str:
    commands = [f"M{num(points[0][0])},{num(points[0][1])}"]
    for index in range(len(points) - 1):
        before = points[index - 1] if index > 0 else points[index]
        start, end = points[index], points[index + 1]
        after = points[index + 2] if index + 2 < len(points) else end
        first = (start[0] + (end[0] - before[0]) / 6, clamp(start[1] + (end[1] - before[1]) / 6, top, bottom))
        second = (end[0] - (after[0] - start[0]) / 6, clamp(end[1] - (after[1] - start[1]) / 6, top, bottom))
        commands.append(
            f"C{num(first[0])},{num(first[1])} {num(second[0])},{num(second[1])} {num(end[0])},{num(end[1])}"
        )
    return "".join(commands)


def wave_path(width: float, baseline: float, amplitude: float, period: float, phase: float, bottom: float, step: float = 20.0) -> str:
    points = []
    for index in range(int(width * 2 / step) + 1):
        x = index * step
        y = baseline + amplitude * math.sin(2 * math.pi * x / period + phase)
        points.append(f"{num(x)},{num(y)}")
    return f"M{' L'.join(points)} L{num(width * 2)},{num(bottom)} L0,{num(bottom)} Z"


def star_icon(cx: float, cy: float, radius: float, fill: str) -> str:
    points = []
    for index in range(10):
        angle = -math.pi / 2 + index * math.pi / 5
        reach = radius if index % 2 == 0 else radius * 0.45
        points.append(f"{num(cx + reach * math.cos(angle))},{num(cy + reach * math.sin(angle))}")
    return el("polygon", points=" ".join(points), fill=fill)


def fork_icon(x: float, y: float, stroke: str) -> str:
    def dot(dx: float, dy: float) -> str:
        return el("circle", cx=x + dx, cy=y + dy, r=1.9, fill="none", stroke=stroke, stroke_width=1.4)

    branch = (
        f"M{num(x + 2)},{num(y + 4)} V{num(y + 6.5)} Q{num(x + 2)},{num(y + 8.5)} {num(x + 6)},{num(y + 8.5)} "
        f"Q{num(x + 10)},{num(y + 8.5)} {num(x + 10)},{num(y + 6.5)} V{num(y + 4)} "
        f"M{num(x + 6)},{num(y + 8.5)} V{num(y + 10)}"
    )
    return "".join(
        (
            el("path", d=branch, fill="none", stroke=stroke, stroke_width=1.4),
            dot(2, 2),
            dot(10, 2),
            dot(6, 12),
        )
    )


BASE_STYLE = "".join(
    (
        "text{font-family:'Segoe UI',-apple-system,BlinkMacSystemFont,Roboto,'Noto Sans','Helvetica Neue',Arial,sans-serif}",
        ".mono{font-family:'SFMono-Regular',Consolas,'Liberation Mono',Menlo,'DejaVu Sans Mono',monospace}",
        ".rise{animation:rise .8s cubic-bezier(.2,.7,.2,1) both}",
        ".fade{animation:fade .9s ease both}",
        ".pop{transform-box:fill-box;transform-origin:center;animation:pop .5s ease both}",
        ".grow{transform-box:fill-box;transform-origin:left center;animation:grow .9s cubic-bezier(.2,.7,.2,1) both}",
        ".ring{animation:ring 1.6s cubic-bezier(.2,.7,.2,1) both}",
        ".draw{stroke-dasharray:1;animation:draw 2.2s ease .3s both}",
        ".blink{animation:blink 1s steps(1) infinite}",
        ".pulse{animation:pulse 2s ease-in-out infinite}",
        ".twinkle{animation:twinkle 4s ease-in-out infinite}",
        ".flicker{transform-box:fill-box;transform-origin:50% 100%;animation:flicker 1.6s ease-in-out infinite}",
        ".sweep{animation:sweep 4.5s linear infinite}",
        ".orb-a{animation:float-a 11s ease-in-out infinite alternate}",
        ".orb-b{animation:float-b 13s ease-in-out infinite alternate}",
        ".wave-a{animation:drift 30s linear infinite}",
        ".wave-b{animation:drift 20s linear infinite reverse}",
        ".wave-c{animation:drift 38s linear infinite}",
        "@keyframes rise{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}",
        "@keyframes fade{from{opacity:0}to{opacity:1}}",
        "@keyframes pop{from{opacity:0;transform:scale(.4)}to{opacity:1;transform:scale(1)}}",
        "@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}",
        "@keyframes ring{from{stroke-dashoffset:100}to{stroke-dashoffset:var(--to)}}",
        "@keyframes draw{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}",
        "@keyframes blink{0%,100%{opacity:1}50%{opacity:0}}",
        "@keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}",
        "@keyframes twinkle{0%,100%{opacity:.15}50%{opacity:1}}",
        "@keyframes flicker{0%,100%{transform:scale(1)}50%{transform:scale(1.1,1.06)}}",
        "@keyframes sweep{from{transform:translateX(0)}to{transform:translateX(940px)}}",
        "@keyframes float-a{from{transform:translate(0,0)}to{transform:translate(70px,22px)}}",
        "@keyframes float-b{from{transform:translate(0,0)}to{transform:translate(-60px,-18px)}}",
        "@keyframes drift{from{transform:translateX(0)}to{transform:translateX(-1000px)}}",
        "@media (prefers-reduced-motion:reduce){*{animation:none!important}}",
    )
)


class Canvas:
    def __init__(self, width: float, height: float, label: str) -> None:
        self.width = width
        self.height = height
        self.label = label
        self.definitions: list[str] = []
        self.rules: list[str] = []
        self.nodes: list[str] = []

    def define(self, *items: str) -> None:
        self.definitions.extend(items)

    def style(self, *rules: str) -> None:
        self.rules.extend(rules)

    def add(self, *items: str) -> None:
        self.nodes.extend(items)

    def render(self) -> str:
        size = f'width="{num(self.width)}" height="{num(self.height)}" viewBox="0 0 {num(self.width)} {num(self.height)}"'
        head = f'<svg xmlns="http://www.w3.org/2000/svg" {size} role="img" aria-label="{esc(self.label)}">'
        return "".join(
            (
                head,
                el("title", esc(self.label)),
                el("defs", *self.definitions),
                el("style", BASE_STYLE, *self.rules),
                *self.nodes,
                "</svg>\n",
            )
        )


def frame(canvas: Canvas, title: str = "", meta: str = "") -> None:
    width, height = canvas.width, canvas.height
    canvas.define(
        linear("card-bg", stop(0, Color.BG), stop(100, Color.BG_SOFT), x2=1, y2=1),
        linear("card-accent", stop(0, Color.BLUE), stop(100, Color.PURPLE), x2=0, y2=1),
        el(
            "pattern",
            el("circle", cx=1, cy=1, r=1, fill="#ffffff", fill_opacity=0.05),
            id="card-dots",
            width=18,
            height=18,
            patternUnits="userSpaceOnUse",
        ),
    )
    canvas.add(
        el("rect", width=width, height=height, rx=20, fill="url(#card-bg)"),
        el("rect", width=width, height=height, rx=20, fill="url(#card-dots)"),
        el("rect", x=0.5, y=0.5, width=width - 1, height=height - 1, rx=19.5, fill="none", stroke=Color.BORDER),
    )
    if title:
        canvas.add(
            el("rect", x=CARD_PAD, y=28, width=5, height=24, rx=2.5, fill="url(#card-accent)"),
            text(title, CARD_PAD + 16, 47, 22, Color.TEXT, 700),
        )
    if meta:
        canvas.add(text(meta, width - CARD_PAD, 46, 15, Color.MUTED, anchor="end"))


def wave_layers(width: float, height: float, layers: Sequence[tuple[float, float, float, float, str, str]]) -> list[str]:
    return [
        el("path", d=wave_path(width, baseline, amplitude, period, phase, height), fill=f"url(#{fill})", class_=motion)
        for baseline, amplitude, period, phase, fill, motion in layers
    ]


def wave_gradients() -> list[str]:
    return [
        linear("wave-a", stop(0, Color.BLUE, 0.36), stop(100, Color.PURPLE, 0.36)),
        linear("wave-b", stop(0, Color.PURPLE, 0.3), stop(100, Color.PINK, 0.3)),
        linear("wave-c", stop(0, Color.CYAN, 0.22), stop(100, Color.BLUE, 0.22)),
    ]


def render_header(identity: Identity) -> str:
    width, height = 1000, 320
    canvas = Canvas(width, height, f"{identity.name} \u2014 {identity.title}")
    rng = random.Random(11)
    canvas.define(
        linear("hero-bg", stop(0, "#080d1c"), stop(52, "#171144"), stop(100, "#0a2d4d"), x2=1, y2=1),
        linear("hero-title", stop(0, "#ffffff"), stop(55, "#a5d6ff"), stop(100, "#d2a8ff")),
        linear("hero-accent", stop(0, Color.BLUE), stop(100, Color.PURPLE)),
        *wave_gradients(),
        radial("orb-blue", Color.BLUE, 0.5),
        radial("orb-purple", Color.PURPLE, 0.5),
        el("clipPath", el("rect", width=width, height=height, rx=28), id="hero-clip"),
        el("filter", el("feGaussianBlur", stdDeviation=9), id="hero-glow", x="-20%", y="-60%", width="140%", height="220%"),
    )
    stars = []
    for _ in range(46):
        stars.append(
            el(
                "circle",
                cx=round(rng.uniform(16, width - 16), 1),
                cy=round(rng.uniform(14, 200), 1),
                r=rng.choice((0.9, 1.2, 1.6, 2.1)),
                fill="#ffffff",
                class_="twinkle",
                style=f"animation-delay:{rng.uniform(0, 5):.2f}s;animation-duration:{rng.uniform(2.6, 5.6):.2f}s",
            )
        )
    waves = wave_layers(
        width,
        height,
        (
            (250, 16, 500, 0.0, "wave-a", "wave-a"),
            (268, 12, 1000 / 3, 1.4, "wave-b", "wave-b"),
            (284, 9, 250, 2.6, "wave-c", "wave-c"),
        ),
    )
    pill_width = 68 + len(identity.status) * 9.0
    pill_x = (width - pill_width) / 2
    pill = el(
        "g",
        el("rect", x=pill_x, y=52, width=pill_width, height=38, rx=19, fill="#ffffff", fill_opacity=0.06, stroke="#ffffff", stroke_opacity=0.16),
        el("circle", cx=pill_x + 24, cy=71, r=5, fill=Color.GREEN, class_="pulse"),
        text(identity.status, pill_x + 42, 77, 16, "#c9d1d9", 500),
        class_="fade",
    )
    title_attributes = dict(x=500, y=184, font_size=84, font_weight=800, text_anchor="middle", letter_spacing=1)
    glow = el("text", esc(identity.name), fill=Color.BLUE, opacity=0.5, filter="url(#hero-glow)", class_="fade", **title_attributes)
    title = el("text", esc(identity.name), fill="url(#hero-title)", class_="rise", **title_attributes)
    subtitle = el(
        "text",
        esc(identity.title.upper()),
        x=500,
        y=228,
        font_size=22,
        font_weight=600,
        letter_spacing=8,
        text_anchor="middle",
        fill="#9fb4ff",
        class_="rise",
        style="animation-delay:.2s",
    )
    underline = el("rect", x=440, y=244, width=120, height=3, rx=1.5, fill="url(#hero-accent)", class_="grow", style="animation-delay:.5s")
    canvas.add(
        el(
            "g",
            el("rect", width=width, height=height, fill="url(#hero-bg)"),
            el("circle", cx=170, cy=70, r=230, fill="url(#orb-blue)", class_="orb-a"),
            el("circle", cx=850, cy=110, r=250, fill="url(#orb-purple)", class_="orb-b"),
            *stars,
            *waves,
            pill,
            glow,
            title,
            subtitle,
            underline,
            clip_path="url(#hero-clip)",
        )
    )
    return canvas.render()


def render_footer(identity: Identity, today: date) -> str:
    width, height = 1000, 240
    canvas = Canvas(width, height, identity.cta_title)
    canvas.define(
        linear("foot-bg", stop(0, "#080d1c"), stop(52, "#171144"), stop(100, "#0a2d4d"), x2=1, y2=1),
        linear("foot-title", stop(0, "#ffffff"), stop(55, "#a5d6ff"), stop(100, "#d2a8ff")),
        *wave_gradients(),
        el("clipPath", el("rect", width=width, height=height, rx=28), id="foot-clip"),
    )
    waves = wave_layers(
        width,
        height,
        (
            (158, 14, 500, 0.6, "wave-a", "wave-a"),
            (176, 10, 1000 / 3, 2.0, "wave-b", "wave-b"),
            (194, 8, 250, 3.2, "wave-c", "wave-c"),
        ),
    )
    canvas.add(
        el(
            "g",
            el("rect", width=width, height=height, fill="url(#foot-bg)"),
            *waves,
            el("text", esc(identity.cta_title), x=500, y=86, font_size=38, font_weight=800, text_anchor="middle", fill="url(#foot-title)", class_="rise"),
            text(identity.cta_text, 500, 126, 18, "#b6c2e2", 400, "middle", class_="rise", style="animation-delay:.15s"),
            text(f"Auto-updated \u00b7 {today:%b} {today.day}, {today.year}", 500, 222, 13, "#ffffff", 500, "middle", fill_opacity=0.55),
            clip_path="url(#foot-clip)",
        )
    )
    return canvas.render()


def typing_schedule(lengths: Sequence[int], type_step: float = 0.07, erase_step: float = 0.03, hold: float = 1.5, gap: float = 0.4):
    clock = 0.0
    schedule = []
    for length in lengths:
        appear = [clock + (index + 1) * type_step for index in range(length)]
        clock = appear[-1] + hold
        vanish = [clock + (length - index) * erase_step for index in range(length)]
        clock = vanish[0] + gap
        schedule.append((appear, vanish))
    return schedule, clock


def render_typing(identity: Identity) -> str:
    width, height, size, origin = CARD_WIDTH, 64, 22, 62
    advance = size * 0.6
    lines = [line.replace(" ", NBSP) for line in identity.taglines]
    schedule, total = typing_schedule([len(line) for line in lines])
    duration = f"{total:.2f}s"
    canvas = Canvas(width, height, " \u00b7 ".join(identity.taglines))
    canvas.define(linear("typing-ink", stop(0, "#79c0ff"), stop(100, "#d2a8ff")))
    canvas.add(
        el("rect", x=0.5, y=0.5, width=width - 1, height=height - 1, rx=16, fill=Color.BG, stroke=Color.BORDER),
        el("text", "$", x=26, y=41, font_size=size, fill=Color.GREEN, font_weight=700, class_="mono"),
    )
    caret_events = [(0.0, origin)]
    for line, (appear, vanish) in zip(lines, schedule):
        for index, moment in enumerate(appear):
            caret_events.append((moment, origin + (index + 1) * advance))
        for index in range(len(line) - 1, -1, -1):
            caret_events.append((vanish[index], origin + index * advance))
    caret_times = ";".join(f"{moment / total:.5f}" for moment, _ in caret_events)
    caret_values = ";".join(num(position) for _, position in caret_events)
    caret = el(
        "rect",
        el("animate", attributeName="x", values=caret_values, keyTimes=caret_times, calcMode="discrete", dur=duration, repeatCount="indefinite"),
        x=origin,
        y=17,
        width=2.5,
        height=30,
        rx=1.2,
        fill=Color.PURPLE,
        class_="blink",
    )
    for row, (line, (appear, vanish)) in enumerate(zip(lines, schedule)):
        glyphs = []
        for index, char in enumerate(line):
            keys = f"0;{appear[index] / total:.5f};{vanish[index] / total:.5f}"
            glyphs.append(
                el(
                    "tspan",
                    esc(char),
                    el("animate", attributeName="fill-opacity", values="0;1;0", keyTimes=keys, calcMode="discrete", dur=duration, repeatCount="indefinite"),
                    fill_opacity=1 if row == 0 else 0,
                )
            )
        canvas.add(
            el(
                "text",
                *glyphs,
                x=origin,
                y=41,
                font_size=size,
                font_weight=600,
                fill="url(#typing-ink)",
                textLength=num(len(line) * advance),
                lengthAdjust="spacing",
                class_="mono",
            )
        )
    canvas.add(caret)
    return canvas.render()


def code_lines(identity: Identity) -> list[list[tuple[str, str]]]:
    keyword, cls, base, var, string, plain = Color.RED, Color.ORANGE, "#79c0ff", "#79c0ff", "#a5d6ff", Color.TEXT
    keys = ("role", "education", "stack", "status", "next_up", "open_to")
    pad = max(len(key) for key in keys)

    def attribute(key: str, value: list[tuple[str, str]]) -> list[tuple[str, str]]:
        return [("    ", plain), (key.ljust(pad), var), (" = ", keyword), *value]

    def quoted(value: str) -> list[tuple[str, str]]:
        return [(f'"{value}"', string)]

    stack_items: list[tuple[str, str]] = [("[", plain)]
    for index, item in enumerate(identity.stack):
        stack_items.append((f'"{item}"', string))
        stack_items.append((", " if index < len(identity.stack) - 1 else "]", plain))

    lines = [
        [("class ", keyword), (identity.class_name, cls), ("(", plain), ("Developer", base), ("):", plain)],
        attribute("role", quoted(identity.role)),
        attribute("education", quoted(identity.education)),
        attribute("stack", stack_items),
        attribute("status", quoted(identity.currently)),
        attribute("next_up", quoted(identity.next_up)),
        attribute("open_to", [("[", plain)]),
    ]
    for item in identity.open_to:
        lines.append([("        ", plain), (f'"{item}"', string), (",", plain)])
    lines.append([("    ", plain), ("]", plain)])
    return lines


def render_about(identity: Identity) -> str:
    lines = code_lines(identity)
    font, line_h, bar = 19, 30, 46
    advance = font * 0.602
    first = bar + 44
    height = first + (len(lines) - 1) * line_h + 38
    canvas = Canvas(CARD_WIDTH, height, f"About {identity.name}")
    frame(canvas)
    bar_path = f"M1,{bar} V21 A20,20 0 0 1 21,1 H{CARD_WIDTH - 21} A20,20 0 0 1 {CARD_WIDTH - 1},21 V{bar} Z"
    canvas.add(
        el("path", d=bar_path, fill=Color.PANEL),
        el("rect", x=1, y=bar, width=CARD_WIDTH - 2, height=1, fill=Color.BORDER),
        el("circle", cx=32, cy=23, r=6.5, fill="#ff5f56"),
        el("circle", cx=54, cy=23, r=6.5, fill="#ffbd2e"),
        el("circle", cx=76, cy=23, r=6.5, fill="#27c93f"),
        text("about.py", CARD_WIDTH / 2, 28, 14, Color.MUTED, 500, "middle", class_="mono"),
    )
    for index, tokens in enumerate(lines):
        y = first + index * line_h
        spans = "".join(el("tspan", esc(chunk.replace(" ", NBSP)), fill=color) for chunk, color in tokens)
        canvas.add(
            el(
                "g",
                el("text", str(index + 1), x=58, y=y, font_size=15, fill="#484f58", text_anchor="end", class_="mono"),
                el("text", spans, x=76, y=y, font_size=font, class_="mono"),
                class_="rise",
                style=f"animation-delay:{0.12 * index:.2f}s",
            )
        )
    last = "".join(chunk for chunk, _ in lines[-1])
    canvas.add(
        el(
            "rect",
            x=76 + len(last) * advance + 3,
            y=first + (len(lines) - 1) * line_h - 19,
            width=10,
            height=24,
            rx=2,
            fill=Color.BLUE,
            fill_opacity=0.85,
            class_="blink",
        )
    )
    return canvas.render()


def render_stats(profile: Profile) -> str:
    tiles = (
        ("Contributions", profile.contributions, Color.BLUE),
        ("Commits", profile.commits, Color.GREEN),
        ("Pull Requests", profile.pull_requests, Color.PURPLE),
        ("Issues", profile.issues, Color.ORANGE),
        ("Code Reviews", profile.reviews, Color.PINK),
        ("Repositories", profile.repo_count, Color.CYAN),
        ("Stars Earned", profile.stars, Color.YELLOW),
        ("Followers", profile.followers, Color.RED),
    )
    columns, gap, tile_h, top = 4, 16, 104, 84
    tile_w = (INNER_WIDTH - gap * (columns - 1)) / columns
    rows = math.ceil(len(tiles) / columns)
    canvas = Canvas(CARD_WIDTH, top + rows * tile_h + (rows - 1) * gap + CARD_PAD, f"GitHub statistics for {profile.login}")
    frame(canvas, "GitHub Stats", f"@{profile.login} \u00b7 all-time")
    for index, (label, value, color) in enumerate(tiles):
        x = CARD_PAD + (index % columns) * (tile_w + gap)
        y = top + (index // columns) * (tile_h + gap)
        canvas.add(
            el(
                "g",
                el("rect", x=x, y=y, width=tile_w, height=tile_h, rx=14, fill=Color.PANEL, fill_opacity=0.9, stroke=Color.BORDER),
                el("circle", cx=x + tile_w - 32, cy=y + 32, r=24, fill=color, fill_opacity=0.09),
                el("rect", x=x + 18, y=y + 18, width=28, height=4, rx=2, fill=color),
                text(human(value), x + 18, y + 66, 38, color, 800),
                text(label, x + 18, y + 90, 15, Color.MUTED, 500),
                class_="rise",
                style=f"animation-delay:{index * 0.07:.2f}s",
            )
        )
    return canvas.render()


def render_streak(profile: Profile) -> str:
    current, longest = compute_streaks(profile.days, profile.today)
    active = [entry.when for entry in profile.days if entry.count > 0]
    since = f"{short_date(min(active), profile.today)} \u2013 Present" if active else "No contributions yet"
    canvas = Canvas(CARD_WIDTH, 280, f"Contribution streak for {profile.login}")
    frame(canvas, "Contribution Streak", "all-time \u00b7 UTC")
    canvas.define(
        linear("ring-ink", stop(0, Color.BLUE), stop(100, Color.PURPLE), x1=0, y1=0, x2=1, y2=1),
        linear("flame-ink", stop(0, "#ffd166"), stop(100, "#ff6b35"), x2=0, y2=1),
    )
    cx, cy, radius = 400, 138, 58
    progress = min(100.0, current.length / longest.length * 100) if longest.length else 0.0
    ring = [el("circle", cx=cx, cy=cy, r=radius, fill="none", stroke="#21262d", stroke_width=9)]
    if progress > 0:
        ring.append(
            el(
                "circle",
                cx=cx,
                cy=cy,
                r=radius,
                fill="none",
                stroke="url(#ring-ink)",
                stroke_width=9,
                stroke_linecap="round",
                pathLength=100,
                stroke_dasharray=100,
                stroke_dashoffset=round(100 - progress, 2),
                transform=f"rotate(-90 {cx} {cy})",
                class_="ring",
                style=f"--to:{100 - progress:.2f}",
            )
        )
    flame = el(
        "g",
        el(
            "path",
            d="M0,-15 C4,-8 10,-4 10,3 C10,10 5,15 0,15 C-5,15 -10,10 -10,3 C-10,-2 -7,-5 -5,-8 C-4,-5 -2,-4 0,-4 C1,-8 1,-12 0,-15 Z",
            fill="url(#flame-ink)",
            class_="flicker",
        ),
        transform=f"translate({cx} {cy - 34})",
    )
    canvas.add(
        el("rect", x=266, y=88, width=1, height=150, fill=Color.BORDER),
        el("rect", x=533, y=88, width=1, height=150, fill=Color.BORDER),
        el(
            "g",
            text(human(profile.contributions), 133, 158, 56, Color.BLUE, 800, "middle"),
            text("Total Contributions", 133, 200, 18, Color.TEXT, 600, "middle"),
            text(since, 133, 226, 15, Color.MUTED, 400, "middle"),
            class_="rise",
            style="animation-delay:.05s",
        ),
        el(
            "g",
            *ring,
            flame,
            text(str(current.length), cx, 162, 44, Color.TEXT, 800, "middle"),
            text("Current Streak", cx, 226, 18, Color.PURPLE, 700, "middle"),
            text(span_label(current, profile.today), cx, 250, 15, Color.MUTED, 400, "middle"),
            class_="rise",
            style="animation-delay:.15s",
        ),
        el(
            "g",
            text(str(longest.length), 667, 158, 56, Color.GREEN, 800, "middle"),
            text("Longest Streak", 667, 200, 18, Color.TEXT, 600, "middle"),
            text(span_label(longest, profile.today), 667, 226, 15, Color.MUTED, 400, "middle"),
            class_="rise",
            style="animation-delay:.25s",
        ),
    )
    return canvas.render()


def render_languages(profile: Profile) -> str:
    shares = language_shares(profile.languages)
    if not shares:
        canvas = Canvas(CARD_WIDTH, 170, "Top languages")
        frame(canvas, "Top Languages", "public repositories")
        canvas.add(text("Language data appears once your repositories have code.", CARD_WIDTH / 2, 118, 18, Color.MUTED, 400, "middle"))
        return canvas.render()
    columns, row_h, bar_y, bar_h, legend_y = 2, 40, 82, 18, 152
    rows = math.ceil(len(shares) / columns)
    canvas = Canvas(CARD_WIDTH, legend_y + (rows - 1) * row_h + 40, "Top languages")
    frame(canvas, "Top Languages", "by code size \u00b7 public repos")
    canvas.define(el("clipPath", el("rect", x=CARD_PAD, y=bar_y, width=INNER_WIDTH, height=bar_h, rx=9), id="bar-clip"))
    raw = [max(INNER_WIDTH * share / 100, 5) for _, share, _ in shares]
    factor = INNER_WIDTH / sum(raw)
    cursor = float(CARD_PAD)
    segments = []
    for index, ((_, _, color), size) in enumerate(zip(shares, raw)):
        width = size * factor
        segments.append(
            el(
                "rect",
                x=cursor,
                y=bar_y,
                width=width,
                height=bar_h,
                fill=color,
                stroke=Color.BG,
                stroke_width=2,
                class_="grow",
                style=f"animation-delay:{index * 0.12:.2f}s",
            )
        )
        cursor += width
    canvas.add(el("g", *segments, clip_path="url(#bar-clip)"))
    column_w = (INNER_WIDTH - 16) / columns
    for index, (name, share, color) in enumerate(shares):
        x = CARD_PAD + (index % columns) * (column_w + 16)
        y = legend_y + (index // columns) * row_h
        canvas.add(
            el(
                "g",
                el("circle", cx=x + 8, cy=y - 6, r=7, fill=color),
                text(shorten(name, 18, placeholder="\u2026"), x + 26, y, 19, Color.TEXT, 600),
                text(f"{share:.1f}%", x + column_w - 8, y, 17, Color.MUTED, 500, "end"),
                class_="rise",
                style=f"animation-delay:{0.25 + index * 0.08:.2f}s",
            )
        )
    return canvas.render()


def render_activity(profile: Profile) -> str:
    start, weeks = activity_window(profile.days, profile.today)
    counts = {entry.when: entry.count for entry in profile.days}
    visible = [start + timedelta(days=offset) for offset in range(weeks * 7) if start + timedelta(days=offset) <= profile.today]
    peak = max((counts.get(day, 0) for day in visible), default=0)
    total = sum(counts.get(day, 0) for day in visible)
    label_w = 40
    pitch = min(28, (INNER_WIDTH - label_w) // weeks)
    gap = 3
    cell = pitch - gap
    grid_w = weeks * pitch - gap
    grid_x = CARD_PAD + label_w + (INNER_WIDTH - label_w - grid_w) / 2
    month_y, grid_y = 92, 104
    grid_h = 7 * pitch - gap
    legend_y = grid_y + grid_h + 34
    trend_y = legend_y + 52
    chart_top = trend_y + 20
    chart_h = 120
    chart_bottom = chart_top + chart_h
    height = chart_bottom + 54
    canvas = Canvas(CARD_WIDTH, height, f"Contribution activity for {profile.login}")
    frame(canvas, "Contribution Activity", f"{total:,} contributions \u00b7 last {weeks} weeks")
    canvas.define(
        linear("trend-line", stop(0, Color.BLUE), stop(55, Color.PURPLE), stop(100, Color.PINK), gradientUnits="userSpaceOnUse", x1=CARD_PAD, x2=CARD_WIDTH - CARD_PAD),
        linear("trend-area", stop(0, Color.PURPLE, 0.35), stop(100, Color.BLUE, 0), x2=0, y2=1),
    )
    cells = []
    for day in visible:
        week, row = divmod((day - start).days, 7)
        cells.append(
            el(
                "rect",
                x=grid_x + week * pitch,
                y=grid_y + row * pitch,
                width=cell,
                height=cell,
                rx=min(4.0, cell / 4),
                fill=Color.HEAT[heat_level(counts.get(day, 0), peak)],
                class_="pop",
                style=f"animation-delay:{week * 0.035:.3f}s",
            )
        )
    canvas.add(el("g", *cells))
    changes: list[tuple[int, int]] = []
    previous_month = None
    for week in range(weeks):
        month = (start + timedelta(weeks=week, days=3)).month
        if month != previous_month:
            changes.append((week, month))
        previous_month = month
    for position, (week, month) in enumerate(changes):
        following = changes[position + 1][0] if position + 1 < len(changes) else weeks
        if position == 0 and following - week < 3:
            continue
        canvas.add(text(f"{date(2000, month, 1):%b}", grid_x + week * pitch, month_y, 13, Color.MUTED, 500))
    for row, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        canvas.add(text(label, grid_x - 10, grid_y + row * pitch + cell * 0.78, 13, Color.MUTED, 500, "end"))
    legend_right = CARD_WIDTH - CARD_PAD
    canvas.add(text("More", legend_right, legend_y, 13, Color.MUTED, 500, "end"))
    swatch_end = legend_right - 42
    for level, color in enumerate(Color.HEAT):
        canvas.add(el("rect", x=swatch_end - (len(Color.HEAT) - level) * 17 + 3, y=legend_y - 11, width=13, height=13, rx=3.5, fill=color))
    canvas.add(text("Less", swatch_end - len(Color.HEAT) * 17 - 2, legend_y, 13, Color.MUTED, 500, "end"))
    best = max(visible, key=lambda day: counts.get(day, 0), default=None)
    if best is not None and counts.get(best, 0) > 0:
        canvas.add(text(f"Best day: {counts[best]} on {short_date(best, profile.today)}", CARD_PAD, legend_y, 14, Color.MUTED, 500))
    else:
        canvas.add(text("Your first contribution lights this up.", CARD_PAD, legend_y, 14, Color.MUTED, 500))
    weekly = []
    for week in range(weeks):
        days = [start + timedelta(days=week * 7 + offset) for offset in range(7)]
        weekly.append(sum(counts.get(day, 0) for day in days if day <= profile.today))
    canvas.add(text("Weekly trend", CARD_PAD, trend_y, 17, Color.TEXT, 600))
    x_start, x_end, headroom = CARD_PAD + 8, CARD_WIDTH - CARD_PAD - 8, 30
    ceiling = max(max(weekly), 1)
    scale = (chart_h - headroom) / ceiling
    for fraction in (0, 0.5, 1):
        y = chart_bottom - fraction * (chart_h - headroom)
        canvas.add(el("line", x1=x_start, y1=y, x2=x_end, y2=y, stroke=Color.BORDER, stroke_dasharray="4 6", stroke_opacity=0.8 if fraction else 1))
    if max(weekly) > 0:
        canvas.add(text(str(ceiling), x_end, chart_bottom - (chart_h - headroom) - 8, 12, Color.MUTED, 500, "end"))
    points = [(x_start + (x_end - x_start) * index / max(weeks - 1, 1), chart_bottom - value * scale) for index, value in enumerate(weekly)]
    line = smooth_path(points, chart_bottom - (chart_h - headroom), chart_bottom)
    area = f"{line} L{num(points[-1][0])},{num(chart_bottom)} L{num(points[0][0])},{num(chart_bottom)} Z"
    canvas.add(
        el("path", d=area, fill="url(#trend-area)", class_="fade", style="animation-delay:.9s"),
        el("path", d=line, fill="none", stroke="url(#trend-line)", stroke_width=3, stroke_linecap="round", stroke_linejoin="round", pathLength=1, class_="draw"),
    )
    if max(weekly) > 0:
        best_week = max(range(weeks), key=weekly.__getitem__)
        px, py = points[best_week]
        label_x = clamp(px, x_start + 46, x_end - 46)
        canvas.add(
            el(
                "g",
                el("circle", cx=px, cy=py, r=9, fill=Color.PURPLE, fill_opacity=0.25),
                el("circle", cx=px, cy=py, r=4.5, fill="#ffffff", stroke=Color.PURPLE, stroke_width=2),
                text(f"Peak {weekly[best_week]}", label_x, py - 16, 13, Color.TEXT, 700, "middle"),
                class_="fade",
                style="animation-delay:2.2s",
            )
        )
    canvas.add(
        text(short_date(start, profile.today), x_start, chart_bottom + 24, 13, Color.MUTED, 500),
        text("This week", x_end, chart_bottom + 24, 13, Color.MUTED, 500, "end"),
    )
    return canvas.render()


def render_projects(profile: Profile) -> str:
    pool = [repo for repo in profile.repos if repo.name.lower() != profile.login.lower()] or list(profile.repos)
    featured = pool[:4]
    top = 84
    if not featured:
        canvas = Canvas(CARD_WIDTH, 170, "Featured repositories")
        frame(canvas, "Featured Repositories")
        canvas.add(text("Public repositories will show up here.", CARD_WIDTH / 2, 118, 18, Color.MUTED, 400, "middle"))
        return canvas.render()
    columns = 1 if len(featured) == 1 else 2
    gap, tile_h = 16, 150
    tile_w = (INNER_WIDTH - gap * (columns - 1)) / columns
    rows = math.ceil(len(featured) / columns)
    canvas = Canvas(CARD_WIDTH, top + rows * tile_h + (rows - 1) * gap + CARD_PAD, "Featured repositories")
    frame(canvas, "Featured Repositories", f"{profile.repo_count} public repos")
    per_line = max(18, int((tile_w - 46) / 9.2))
    name_limit = max(14, int((tile_w - 46 - 76) / 11.8))
    for index, repo in enumerate(featured):
        x = CARD_PAD + (index % columns) * (tile_w + gap)
        y = top + (index // columns) * (tile_h + gap)
        lines = wrap(repo.description, width=per_line) if repo.description else []
        if len(lines) > 2:
            lines = [lines[0], shorten(" ".join(lines[1:]), width=per_line, placeholder="\u2026")]
        body = [
            el("rect", x=x, y=y, width=tile_w, height=tile_h, rx=16, fill=Color.PANEL, fill_opacity=0.9, stroke=Color.BORDER),
            el("rect", x=x, y=y + 22, width=4, height=34, rx=2, fill=repo.color if repo.language else Color.BLUE),
            text(shorten(repo.name, name_limit, placeholder="\u2026"), x + 24, y + 42, 22, Color.BLUE, 700),
            el("rect", x=x + tile_w - 78, y=y + 22, width=58, height=24, rx=12, fill="none", stroke=Color.BORDER),
            text("Public", x + tile_w - 49, y + 39, 12, Color.MUTED, 600, "middle"),
        ]
        if lines:
            for offset, line in enumerate(lines):
                body.append(text(line, x + 24, y + 74 + offset * 22, 16, "#b6c2d4"))
        else:
            body.append(text("No description yet", x + 24, y + 74, 16, Color.MUTED, font_style="italic"))
        base = y + tile_h - 24
        cursor = x + 24
        if repo.language:
            body.append(el("circle", cx=cursor + 6, cy=base - 5, r=6, fill=repo.color))
            body.append(text(repo.language, cursor + 20, base, 15, Color.TEXT, 500))
            cursor += 20 + len(repo.language) * 8.6 + 24
        stars, forks = human(repo.stars), human(repo.forks)
        body.append(star_icon(cursor + 7, base - 6, 7.5, Color.YELLOW))
        body.append(text(stars, cursor + 21, base, 15, Color.MUTED, 500))
        cursor += 21 + len(stars) * 9 + 24
        body.append(fork_icon(cursor, base - 13, Color.MUTED))
        body.append(text(forks, cursor + 19, base, 15, Color.MUTED, 500))
        canvas.add(el("g", *body, class_="rise", style=f"animation-delay:{index * 0.1:.2f}s"))
    return canvas.render()


def render_divider() -> str:
    canvas = Canvas(CARD_WIDTH, 14, "Section divider")
    canvas.define(
        linear("rule", stop(0, Color.BLUE, 0), stop(30, Color.BLUE, 0.9), stop(70, Color.PURPLE, 0.9), stop(100, Color.PURPLE, 0)),
        linear("beam", stop(0, "#ffffff", 0), stop(50, "#ffffff", 1), stop(100, "#ffffff", 0)),
    )
    canvas.add(
        el("rect", x=0, y=6, width=CARD_WIDTH, height=2, rx=1, fill="url(#rule)"),
        el("rect", x=-140, y=5, width=140, height=4, rx=2, fill="url(#beam)", class_="sweep"),
    )
    return canvas.render()


def build_assets(profile: Profile, identity: Identity) -> dict[str, str]:
    return {
        "header.svg": render_header(identity),
        "typing.svg": render_typing(identity),
        "about.svg": render_about(identity),
        "stats.svg": render_stats(profile),
        "streak.svg": render_streak(profile),
        "languages.svg": render_languages(profile),
        "activity.svg": render_activity(profile),
        "projects.svg": render_projects(profile),
        "divider.svg": render_divider(),
        "footer.svg": render_footer(identity, profile.today),
    }


def write_assets(assets: dict[str, str], directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, content in assets.items():
        target = directory / name
        if not target.exists() or target.read_text(encoding="utf-8") != content:
            target.write_text(content, encoding="utf-8")
        print(f"{name:<15}{len(content.encode('utf-8')):>8} bytes")


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN", "")
    login = os.environ.get("PROFILE_LOGIN") or os.environ.get("GITHUB_REPOSITORY_OWNER", "")
    if not token or not login:
        print("GITHUB_TOKEN and PROFILE_LOGIN (or GITHUB_REPOSITORY_OWNER) must be set", file=sys.stderr)
        return 2
    try:
        profile = fetch_profile(GitHubClient(token), login)
    except GitHubError as error:
        print(f"GitHub API error: {error}", file=sys.stderr)
        return 1
    write_assets(build_assets(profile, IDENTITY), ASSETS_DIR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
