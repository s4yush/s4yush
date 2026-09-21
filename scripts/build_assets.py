from __future__ import annotations

import base64
import json
import math
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from textwrap import shorten, wrap
from typing import Callable, Sequence
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
UTC_OFFSET_HOURS = 5.5
MUSIC_TRACKS = 5
BLANK_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="1" viewBox="0 0 800 1"/>\n'


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
class Commit:
    repo: str
    message: str
    when: datetime
    additions: int
    deletions: int
    files: int


@dataclass(frozen=True)
class Track:
    title: str
    artist: str
    cover: str = ""
    plays: int = 0
    popularity: int = 0
    when: datetime | None = None
    playing: bool = False


@dataclass(frozen=True)
class Artist:
    name: str
    image: str = ""
    plays: int = 0
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class Music:
    source: str
    period: str
    current: Track | None
    top_tracks: tuple[Track, ...]
    top_artists: tuple[Artist, ...]
    genres: tuple[tuple[str, int], ...]
    stats: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Waka:
    total: str
    daily_average: str
    all_time: str
    best_day: str
    languages: tuple[tuple[str, float, str], ...]
    editors: tuple[tuple[str, float, str], ...]
    systems: tuple[tuple[str, float, str], ...]


@dataclass(frozen=True)
class Achievement:
    title: str
    blurb: str
    icon: str
    value: int
    tiers: tuple[int, int, int, int]

    @property
    def tier(self) -> int:
        return sum(1 for limit in self.tiers if self.value >= limit)

    @property
    def target(self) -> int | None:
        return self.tiers[self.tier] if self.tier < len(self.tiers) else None

    @property
    def progress(self) -> float:
        if self.target is None:
            return 1.0
        floor = self.tiers[self.tier - 1] if self.tier else 0
        return max(0.0, min(1.0, (self.value - floor) / (self.target - floor)))


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
    user_id: str = ""
    name: str = ""
    avatar: str = ""
    following: int = 0
    gists: int = 0
    orgs: int = 0
    starred: int = 0
    contributed_to: int = 0
    merged_prs: int = 0
    commit_log: tuple[Commit, ...] = ()

    @property
    def stars(self) -> int:
        return sum(repo.stars for repo in self.repos)

    @property
    def forks(self) -> int:
        return sum(repo.forks for repo in self.repos)

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
id
name
avatarUrl(size: 200)
createdAt
followers { totalCount }
following { totalCount }
gists(privacy: PUBLIC) { totalCount }
organizations { totalCount }
starredRepositories { totalCount }
repositoriesContributedTo(first: 1, contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, PULL_REQUEST_REVIEW]) { totalCount }
mergedPullRequests: pullRequests(states: MERGED) { totalCount }
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


def parse_profile(user: dict, today: date, avatar: str = "", commits: tuple[Commit, ...] = ()) -> Profile:
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
        user_id=user.get("id", ""),
        name=user.get("name") or "",
        avatar=avatar,
        following=user["following"]["totalCount"],
        gists=user["gists"]["totalCount"],
        orgs=user["organizations"]["totalCount"],
        starred=user["starredRepositories"]["totalCount"],
        contributed_to=user["repositoriesContributedTo"]["totalCount"],
        merged_prs=user["mergedPullRequests"]["totalCount"],
        commit_log=commits,
    )


def fetch_profile(client: GitHubClient, login: str, now: datetime | None = None) -> Profile:
    now = now or datetime.now(timezone.utc)
    seed = client.execute("query($login: String!) { user(login: $login) { id createdAt } }", {"login": login})
    if seed.get("user") is None:
        raise GitHubError(f"GitHub user '{login}' was not found")
    created = datetime.fromisoformat(seed["user"]["createdAt"].replace("Z", "+00:00"))
    selections = "\n".join(collection_selection(*window) for window in year_windows(created, now))
    document = f"query($login: String!) {{ user(login: $login) {{ {PROFILE_FIELDS} {selections} }} }}"
    user = client.execute(document, {"login": login})["user"]
    try:
        history = client.execute(COMMIT_QUERY, {"login": login, "id": seed["user"]["id"]})["user"]
        commits = parse_commits(history)
    except (GitHubError, KeyError, TypeError) as error:
        print(f"Commit history unavailable: {error}", file=sys.stderr)
        commits = ()
    return parse_profile(user, now.date(), fetch_data_uri(user.get("avatarUrl", "")), commits)


COMMIT_QUERY = """
query($login: String!, $id: ID!) {
  user(login: $login) {
    repositories(first: 25, ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false, orderBy: {field: PUSHED_AT, direction: DESC}) {
      nodes {
        name
        defaultBranchRef {
          target {
            ... on Commit {
              history(first: 100, author: {id: $id}) {
                nodes { messageHeadline committedDate additions deletions changedFilesIfAvailable }
              }
            }
          }
        }
      }
    }
  }
}
"""

LASTFM_PLACEHOLDER = "2a96cbd8b46e442fc41c2b86b821562f"
SOFT_ERRORS = (urllib.error.URLError, TimeoutError, KeyError, IndexError, TypeError, ValueError)


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_commits(user: dict) -> tuple[Commit, ...]:
    commits = []
    for repo in user["repositories"]["nodes"]:
        target = (repo.get("defaultBranchRef") or {}).get("target") or {}
        for node in (target.get("history") or {}).get("nodes", []):
            commits.append(
                Commit(
                    repo=repo["name"],
                    message=node["messageHeadline"],
                    when=parse_time(node["committedDate"]),
                    additions=node["additions"],
                    deletions=node["deletions"],
                    files=node.get("changedFilesIfAvailable") or 0,
                )
            )
    commits.sort(key=lambda commit: commit.when, reverse=True)
    return tuple(commits)


def fetch_data_uri(url: str) -> str:
    if not url:
        return ""
    request = urllib.request.Request(url, headers={"User-Agent": "profile-assets-builder"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            kind = response.headers.get_content_type()
            payload = response.read(400_000)
    except (urllib.error.URLError, TimeoutError, ValueError):
        return ""
    if not kind.startswith("image/") or len(payload) >= 400_000:
        return ""
    return f"data:{kind};base64,{base64.b64encode(payload).decode('ascii')}"


def http_json(url: str, headers: dict[str, str] | None = None, data: bytes | None = None, timeout: int = 30) -> dict | None:
    request = urllib.request.Request(url, data=data, headers={"User-Agent": "profile-assets-builder", **(headers or {})})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status == 204:
            return None
        return json.load(response)


def as_list(value: object) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


class SpotifyClient:
    def __init__(self, client_id: str, client_secret: str, refresh_token: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.access = ""

    def token(self) -> str:
        if not self.access:
            credentials = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
            body = urllib.parse.urlencode({"grant_type": "refresh_token", "refresh_token": self.refresh_token}).encode()
            headers = {"Authorization": f"Basic {credentials}", "Content-Type": "application/x-www-form-urlencoded"}
            self.access = http_json("https://accounts.spotify.com/api/token", headers, body)["access_token"]
        return self.access

    def get(self, path: str, **params: object) -> dict | None:
        query = urllib.parse.urlencode(params)
        url = f"https://api.spotify.com/v1{path}" + (f"?{query}" if query else "")
        return http_json(url, {"Authorization": f"Bearer {self.token()}"})


def spotify_cover(images: Sequence[dict], minimum: int = 64) -> str:
    usable = sorted((image for image in images if image.get("url")), key=lambda image: image.get("width") or 0)
    if not usable:
        return ""
    pick = next((image for image in usable if (image.get("width") or 0) >= minimum), usable[-1])
    return fetch_data_uri(pick["url"])


def spotify_track(item: dict, played_at: str | None = None, playing: bool = False) -> Track:
    return Track(
        title=item["name"],
        artist=", ".join(artist["name"] for artist in item.get("artists", [])[:2]),
        cover=spotify_cover(item.get("album", {}).get("images", [])),
        popularity=item.get("popularity", 0),
        when=parse_time(played_at) if played_at else None,
        playing=playing,
    )


def fetch_spotify(client: SpotifyClient) -> Music:
    live = client.get("/me/player/currently-playing") or {}
    recent = (client.get("/me/player/recently-played", limit=50) or {}).get("items", [])
    tracks = client.get("/me/top/tracks", limit=MUSIC_TRACKS, time_range="short_term")["items"]
    artists = client.get("/me/top/artists", limit=10, time_range="short_term")["items"]
    item = live.get("item")
    if item and item.get("type") == "track":
        current = spotify_track(item, playing=bool(live.get("is_playing")))
    elif recent:
        current = spotify_track(recent[0]["track"], recent[0]["played_at"])
    else:
        current = None
    minutes = round(sum(entry["track"].get("duration_ms", 0) for entry in recent) / 60000)
    genres = Counter(genre for artist in artists for genre in artist.get("genres", []))
    return Music(
        source="Spotify",
        period="last 4 weeks",
        current=current,
        top_tracks=tuple(spotify_track(entry) for entry in tracks[:MUSIC_TRACKS]),
        top_artists=tuple(
            Artist(
                name=artist["name"],
                image=spotify_cover(artist.get("images", []), 100),
                tags=tuple(artist.get("genres", [])[:2]),
            )
            for artist in artists[:5]
        ),
        genres=tuple(genres.most_common(6)),
        stats=(("Recent plays", f"{len(recent)} tracks"), ("Minutes listened", f"{minutes:,}")),
    )


class LastFmClient:
    def __init__(self, api_key: str, username: str) -> None:
        self.api_key = api_key
        self.username = username

    def call(self, method: str, **params: object) -> dict:
        query = urllib.parse.urlencode(
            {"method": method, "user": self.username, "api_key": self.api_key, "format": "json", **params}
        )
        payload = http_json(f"https://ws.audioscrobbler.com/2.0/?{query}")
        if not payload or "error" in payload:
            raise ValueError(f"Last.fm {method}: {payload}")
        return payload


def lastfm_cover(images: Sequence[dict]) -> str:
    url = next((image.get("#text", "") for image in images if image.get("size") == "medium"), "")
    return "" if not url or LASTFM_PLACEHOLDER in url else fetch_data_uri(url)


def fetch_lastfm(client: LastFmClient) -> Music:
    recent = as_list(client.call("user.getrecenttracks", limit=10)["recenttracks"].get("track"))
    tops = as_list(client.call("user.gettoptracks", period="1month", limit=MUSIC_TRACKS)["toptracks"].get("track"))
    artists = as_list(client.call("user.gettopartists", period="1month", limit=5)["topartists"].get("artist"))
    info = client.call("user.getinfo")["user"]
    current = None
    if recent:
        first = recent[0]
        stamp = (first.get("date") or {}).get("uts")
        current = Track(
            title=first["name"],
            artist=first["artist"]["#text"],
            cover=lastfm_cover(first.get("image", [])),
            when=datetime.fromtimestamp(int(stamp), timezone.utc) if stamp else None,
            playing=(first.get("@attr") or {}).get("nowplaying") == "true",
        )
    tags: dict[str, tuple[str, ...]] = {}
    for artist in artists:
        try:
            listing = as_list(client.call("artist.gettoptags", artist=artist["name"])["toptags"].get("tag"))
            tags[artist["name"]] = tuple(tag["name"] for tag in listing[:3])
        except SOFT_ERRORS:
            tags[artist["name"]] = ()
    genres = Counter(tag for values in tags.values() for tag in values)
    since = datetime.fromtimestamp(int(info["registered"]["unixtime"]), timezone.utc).year
    return Music(
        source="Last.fm",
        period="last 30 days",
        current=current,
        top_tracks=tuple(
            Track(
                title=entry["name"],
                artist=entry["artist"]["name"],
                cover=lastfm_cover(entry.get("image", [])),
                plays=int(entry.get("playcount", 0)),
            )
            for entry in tops[:MUSIC_TRACKS]
        ),
        top_artists=tuple(
            Artist(
                name=artist["name"],
                image=lastfm_cover(artist.get("image", [])),
                plays=int(artist.get("playcount", 0)),
                tags=tags.get(artist["name"], ())[:2],
            )
            for artist in artists[:5]
        ),
        genres=tuple(genres.most_common(6)),
        stats=(("Total scrobbles", f"{int(info['playcount']):,}"), ("Scrobbling since", str(since))),
    )


def load_music() -> Music | None:
    spotify_keys = ("SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET", "SPOTIFY_REFRESH_TOKEN")
    lastfm_keys = ("LASTFM_API_KEY", "LASTFM_USERNAME")
    providers = []
    if all(os.environ.get(key) for key in spotify_keys):
        providers.append(("Spotify", lambda: fetch_spotify(SpotifyClient(*(os.environ[key] for key in spotify_keys)))))
    if all(os.environ.get(key) for key in lastfm_keys):
        providers.append(("Last.fm", lambda: fetch_lastfm(LastFmClient(*(os.environ[key] for key in lastfm_keys)))))
    for name, loader in providers:
        try:
            return loader()
        except SOFT_ERRORS as error:
            print(f"{name} unavailable: {error}", file=sys.stderr)
    return None


class WakaClient:
    def __init__(self, api_key: str) -> None:
        token = base64.b64encode(api_key.encode()).decode()
        self.headers = {"Authorization": f"Basic {token}"}

    def get(self, path: str) -> dict:
        payload: dict = {}
        for attempt in range(3):
            payload = http_json(f"https://wakatime.com/api/v1{path}", self.headers) or {}
            if payload.get("data", {}).get("is_up_to_date", True):
                break
            time.sleep(3)
        return payload["data"]


def waka_rows(items: Sequence[dict], limit: int = 5) -> tuple[tuple[str, float, str], ...]:
    return tuple((item["name"], float(item["percent"]), item.get("text", "")) for item in items[:limit])


def fetch_waka(client: WakaClient, today: date) -> Waka:
    stats = client.get("/users/current/stats/last_7_days")
    try:
        all_time = client.get("/users/current/all_time_since_today")["text"]
    except SOFT_ERRORS:
        all_time = "\u2014"
    best = stats.get("best_day") or {}
    best_label = f"{short_date(date.fromisoformat(best['date']), today)} \u00b7 {best['text']}" if best.get("date") else "\u2014"
    return Waka(
        total=stats["human_readable_total"],
        daily_average=stats["human_readable_daily_average"],
        all_time=all_time,
        best_day=best_label,
        languages=waka_rows(stats.get("languages", [])),
        editors=waka_rows(stats.get("editors", []), 3),
        systems=waka_rows(stats.get("operating_systems", []), 3),
    )


def load_waka(today: date) -> Waka | None:
    key = os.environ.get("WAKATIME_API_KEY", "")
    if not key:
        return None
    try:
        return fetch_waka(WakaClient(key), today)
    except SOFT_ERRORS as error:
        print(f"WakaTime unavailable: {error}", file=sys.stderr)
        return None


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


WINDOWS = (
    ("Night Owl", "10 PM \u2013 5 AM", (22, 23, 0, 1, 2, 3, 4)),
    ("Early Bird", "5 AM \u2013 9 AM", (5, 6, 7, 8)),
    ("Daylight Coder", "9 AM \u2013 6 PM", tuple(range(9, 18))),
    ("Evening Builder", "6 PM \u2013 10 PM", (18, 19, 20, 21)),
)
LEVEL_TITLES = ((1, "Rookie"), (3, "Explorer"), (5, "Builder"), (8, "Hacker"), (12, "Engineer"), (18, "Architect"), (26, "Legend"))
TIER_NAMES = ("Locked", "Bronze", "Silver", "Gold", "Platinum")
TIER_COLORS = ("#3d444d", "#cd7f32", "#c9d1d9", "#ffd166", "#7ee7ff")


def local_time(moment: datetime) -> datetime:
    return moment.astimezone(timezone(timedelta(hours=UTC_OFFSET_HOURS)))


def hour_histogram(commits: Sequence[Commit]) -> list[int]:
    buckets = [0] * 24
    for commit in commits:
        buckets[local_time(commit.when).hour] += 1
    return buckets


def weekday_histogram(days: Sequence[Day]) -> list[int]:
    totals = [0] * 7
    for entry in days:
        totals[(entry.when.weekday() + 1) % 7] += entry.count
    return totals


def chronotype(hours: Sequence[int]) -> tuple[str, str, str]:
    total = sum(hours)
    if total < 5:
        return "Warming Up", "Ship a few more commits to reveal your rhythm", ""
    scored = [(sum(hours[hour] for hour in members), name, span) for name, span, members in WINDOWS]
    best, name, span = max(scored)
    return name, f"{best / total * 100:.0f}% of your commits land between {span}", span


def code_totals(commits: Sequence[Commit]) -> tuple[int, int, int]:
    return (
        sum(commit.additions for commit in commits),
        sum(commit.deletions for commit in commits),
        sum(commit.files for commit in commits),
    )


def experience(profile: Profile) -> int:
    return (
        profile.contributions
        + 2 * profile.commits
        + 5 * profile.pull_requests
        + 4 * profile.merged_prs
        + 3 * profile.issues
        + 4 * profile.reviews
        + 10 * profile.stars
        + 5 * profile.followers
    )


def level_for(xp: int) -> tuple[int, int, int]:
    level = int(math.sqrt(xp / 40)) + 1
    return level, 40 * (level - 1) ** 2, 40 * level**2


def level_title(level: int) -> str:
    return [title for minimum, title in LEVEL_TITLES if level >= minimum][-1]


def ago(moment: datetime, now: datetime) -> str:
    minutes = max(int((now - moment).total_seconds()), 0) // 60
    if minutes < 1:
        return "just now"
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    if days < 14:
        return f"{days}d ago"
    return f"{days // 7}w ago" if days < 60 else f"{days // 30}mo ago"


def evaluate_achievements(profile: Profile) -> list[Achievement]:
    _, longest = compute_streaks(profile.days, profile.today)
    hours = hour_histogram(profile.commit_log)
    added, removed, _ = code_totals(profile.commit_log)
    active = [entry for entry in profile.days if entry.count > 0]
    night = sum(hours[hour] for hour in (22, 23, 0, 1, 2, 3, 4))
    early = sum(hours[5:9])
    return [
        Achievement("Commit Machine", "Commits shipped", "commits", profile.commits, (10, 100, 500, 2000)),
        Achievement("Streak Keeper", "Longest daily streak", "streak", longest.length, (3, 7, 30, 100)),
        Achievement("Merge Master", "Pull requests merged", "merged", profile.merged_prs, (1, 10, 50, 200)),
        Achievement("Star Collector", "Stars earned", "stars", profile.stars, (1, 10, 50, 250)),
        Achievement("Polyglot", "Languages used", "languages", len(profile.languages), (2, 4, 6, 10)),
        Achievement("Code Reviewer", "Reviews given", "reviews", profile.reviews, (1, 10, 50, 200)),
        Achievement("Issue Hunter", "Issues opened", "issues", profile.issues, (1, 10, 50, 200)),
        Achievement("Rising Dev", "Followers", "followers", profile.followers, (1, 10, 50, 250)),
        Achievement("Repo Builder", "Public repositories", "repos", profile.repo_count, (1, 5, 15, 40)),
        Achievement("Consistency", "Active days", "active", len(active), (7, 30, 100, 300)),
        Achievement("Night Owl", "Late-night commits", "night", night, (5, 25, 100, 300)),
        Achievement("Early Bird", "Early commits", "early", early, (5, 25, 100, 300)),
        Achievement("Weekend Warrior", "Weekend active days", "weekend", sum(1 for e in active if e.when.weekday() >= 5), (2, 8, 26, 60)),
        Achievement("Code Volume", "Lines changed", "lines", added + removed, (500, 5000, 25000, 100000)),
        Achievement("Veteran", "Days on GitHub", "veteran", (profile.today - profile.created).days, (30, 365, 730, 1825)),
        Achievement("Explorer", "Repos contributed to", "explorer", profile.contributed_to, (1, 5, 15, 40)),
    ]


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
    return el("polygon", points=star_points(cx, cy, radius), fill=fill)


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
        ".seg{animation:seg 1.2s cubic-bezier(.2,.7,.2,1) both}",
        ".bar{transform-box:fill-box;transform-origin:bottom;animation:bar .8s cubic-bezier(.2,.7,.2,1) both}",
        ".eq{transform-box:fill-box;transform-origin:bottom;animation:eq .9s ease-in-out infinite alternate}",
        "@keyframes seg{from{stroke-dasharray:0 100}}",
        "@keyframes bar{from{transform:scaleY(0)}to{transform:scaleY(1)}}",
        "@keyframes eq{from{transform:scaleY(.25)}to{transform:scaleY(1)}}",
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


FLAME_PATH = "M0,-15 C4,-8 10,-4 10,3 C10,10 5,15 0,15 C-5,15 -10,10 -10,3 C-10,-2 -7,-5 -5,-8 C-4,-5 -2,-4 0,-4 C1,-8 1,-12 0,-15 Z"
RAYS = " ".join(
    f"M{num(7 * math.cos(k * math.pi / 4))},{num(7 * math.sin(k * math.pi / 4))} L{num(10.5 * math.cos(k * math.pi / 4))},{num(10.5 * math.sin(k * math.pi / 4))}"
    for k in range(8)
)
SPOTIFY_GREEN = "#1db954"
LASTFM_RED = "#e5372e"
PALETTE = (Color.BLUE, Color.PURPLE, Color.PINK, Color.ORANGE, Color.GREEN)

ICONS: dict[str, Callable[[str, dict], list[str]]] = {
    "commits": lambda color, s: [el("circle", r=4.5, **s), el("path", d="M-11,0 H-4.5 M4.5,0 H11", **s)],
    "streak": lambda color, s: [el("path", d=FLAME_PATH, fill=color, transform="scale(.66)")],
    "merged": lambda color, s: [
        el("circle", cx=-6, cy=-7, r=2.6, **s),
        el("circle", cx=-6, cy=7, r=2.6, **s),
        el("circle", cx=7, cy=7, r=2.6, **s),
        el("path", d="M-6,-4.4 V4.4 M-3.4,7 H4.4", **s),
    ],
    "stars": lambda color, s: [el("polygon", points=star_points(0, 0.5, 10.5), **s)],
    "languages": lambda color, s: [el("path", d="M-4,-6 L-10,0 L-4,6 M4,-6 L10,0 L4,6 M2,-8 L-2,8", **s)],
    "reviews": lambda color, s: [el("path", d="M-11,0 Q0,-9 11,0 Q0,9 -11,0 Z", **s), el("circle", r=3, **s)],
    "issues": lambda color, s: [el("circle", r=9, **s), el("path", d="M0,-4.5 V1", **s), el("circle", cy=5, r=0.8, fill=color, stroke=color)],
    "followers": lambda color, s: [el("circle", cy=-4, r=3.8, **s), el("path", d="M-8,9 Q-8,2 0,2 Q8,2 8,9", **s)],
    "repos": lambda color, s: [el("rect", x=-7, y=-9, width=14, height=18, rx=2, **s), el("path", d="M-3,-4 H3 M-3,0 H3", **s)],
    "active": lambda color, s: [el("rect", x=-9, y=-7, width=18, height=16, rx=2, **s), el("path", d="M-9,-2 H9 M-4,-10 V-5 M4,-10 V-5", **s)],
    "night": lambda color, s: [el("path", d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z", transform="translate(-12 -12)", **s)],
    "early": lambda color, s: [el("circle", r=4, **s), el("path", d=RAYS, **s)],
    "weekend": lambda color, s: [el("polygon", points="2,-10 -6,2 0,2 -2,10 6,-3 0,-3", **s)],
    "lines": lambda color, s: [el("path", d="M-10,6 L-3,-1 L1,3 L9,-6 M4,-6 H9 V-1", **s)],
    "veteran": lambda color, s: [el("path", d="M0,-10 L8,-6 V1 Q8,7 0,10 Q-8,7 -8,1 V-6 Z M-3,0 L-0.5,3 L4,-3", **s)],
    "explorer": lambda color, s: [
        el("circle", r=9, **s),
        el("polygon", points="4,-4 -1.5,-1.5 -4,4 1.5,1.5", fill=color, fill_opacity=0.35, stroke=color, stroke_width=1.5, stroke_linejoin="round"),
    ],
    "forks": lambda color, s: [
        el("circle", cx=-6, cy=-8, r=2.4, **s),
        el("circle", cx=6, cy=-8, r=2.4, **s),
        el("circle", cy=9.5, r=2.4, **s),
        el("path", d="M-6,-5.6 V-1 Q-6,3 0,3 Q6,3 6,-1 V-5.6 M0,3 V7.1", **s),
    ],
}


def star_points(cx: float, cy: float, radius: float) -> str:
    points = []
    for index in range(10):
        angle = -math.pi / 2 + index * math.pi / 5
        reach = radius if index % 2 == 0 else radius * 0.45
        points.append(f"{num(cx + reach * math.cos(angle))},{num(cy + reach * math.sin(angle))}")
    return " ".join(points)


def icon(name: str, color: str, x: float = 0, y: float = 0, scale: float = 1.0) -> str:
    style = dict(fill="none", stroke=color, stroke_width=2, stroke_linecap="round", stroke_linejoin="round")
    return el("g", *ICONS[name](color, style), transform=f"translate({num(x)} {num(y)}) scale({num(scale)})")


def hexagon(cx: float, cy: float, radius: float) -> str:
    return " ".join(
        f"{num(cx + radius * math.cos(math.radians(-90 + 60 * k)))},{num(cy + radius * math.sin(math.radians(-90 + 60 * k)))}"
        for k in range(6)
    )


def add_cover(canvas: Canvas, ident: str, x: float, y: float, size: float, radius: float, uri: str, label: str, colors: tuple[str, str]) -> None:
    canvas.define(
        el("clipPath", el("rect", x=x, y=y, width=size, height=size, rx=radius), id=ident),
        linear(f"{ident}-fill", stop(0, colors[0]), stop(100, colors[1]), x1=0, y1=0, x2=1, y2=1),
    )
    canvas.add(
        el("rect", x=x, y=y, width=size, height=size, rx=radius, fill=f"url(#{ident}-fill)"),
        text(label, x + size / 2, y + size * 0.66, size * 0.42, "#ffffff", 800, "middle", fill_opacity=0.9),
    )
    if uri:
        canvas.add(el("image", href=uri, x=x, y=y, width=size, height=size, preserveAspectRatio="xMidYMid slice", clip_path=f"url(#{ident})"))


def render_bars(values: Sequence[float], x: float, baseline: float, width: float, height: float, colors: Sequence[str], gap: float = 6) -> list[str]:
    count = len(values)
    bar_width = (width - gap * (count - 1)) / count
    peak = max(max(values), 1)
    bars = []
    for index, value in enumerate(values):
        bar_height = max(value / peak * height, 5.0)
        bars.append(
            el(
                "rect",
                x=x + index * (bar_width + gap),
                y=baseline - bar_height,
                width=bar_width,
                height=bar_height,
                rx=min(6.0, bar_width / 3),
                fill=colors[index] if value else "#21262d",
                fill_opacity=1.0 if value == peak else 0.78,
                class_="bar",
                style=f"animation-delay:{index * 0.03:.2f}s",
            )
        )
    return bars


def render_profile(profile: Profile, identity: Identity) -> str:
    xp = experience(profile)
    level, floor_xp, ceil_xp = level_for(xp)
    rank = level_title(level)
    display = shorten(profile.name or identity.name, 26, placeholder="\u2026")
    canvas = Canvas(CARD_WIDTH, 340, f"Developer profile of {profile.login}: level {level}, {rank}")
    frame(canvas, "Developer Profile", f"@{profile.login}")
    cx, cy, radius = 100, 152, 54
    bar_x = 196
    bar_w = CARD_WIDTH - CARD_PAD - bar_x
    fraction = (xp - floor_xp) / (ceil_xp - floor_xp)
    canvas.define(
        el("clipPath", el("circle", cx=cx, cy=cy, r=radius), id="avatar-clip"),
        linear("avatar-ring", stop(0, Color.BLUE), stop(100, Color.PURPLE), x1=0, y1=0, x2=1, y2=1),
        linear("xp-fill", stop(0, Color.BLUE), stop(60, Color.PURPLE), stop(100, Color.PINK)),
    )
    initials = "".join(part[0] for part in display.split()[:2]).upper() or profile.login[:1].upper()
    canvas.add(
        el("circle", cx=cx, cy=cy, r=radius, fill="url(#avatar-ring)"),
        text(initials, cx, cy + 14, 40, "#ffffff", 800, "middle"),
    )
    if profile.avatar:
        canvas.add(el("image", href=profile.avatar, x=cx - radius, y=cy - radius, width=radius * 2, height=radius * 2, preserveAspectRatio="xMidYMid slice", clip_path="url(#avatar-clip)"))
    canvas.add(
        el("circle", cx=cx, cy=cy, r=radius + 6, fill="none", stroke="url(#avatar-ring)", stroke_width=3),
        el(
            "g",
            text(display, bar_x, 128, 32, Color.TEXT, 800),
            text(f"@{profile.login}  \u00b7  Member since {profile.created:%b %Y}", bar_x, 156, 16, Color.MUTED),
            text(f"LEVEL {level}  \u00b7  {rank.upper()}", bar_x, 202, 15, Color.BLUE, 700, letter_spacing=1.5),
            text(f"{xp:,} / {ceil_xp:,} XP", CARD_WIDTH - CARD_PAD, 202, 15, Color.MUTED, 600, "end"),
            el("rect", x=bar_x, y=214, width=bar_w, height=14, rx=7, fill="#21262d"),
            el("rect", x=bar_x, y=214, width=max(bar_w * fraction, 14), height=14, rx=7, fill="url(#xp-fill)", class_="grow", style="animation-delay:.3s"),
            class_="rise",
        ),
        el("rect", x=CARD_PAD, y=252, width=INNER_WIDTH, height=1, fill=Color.BORDER),
    )
    row = (
        ("Followers", profile.followers),
        ("Following", profile.following),
        ("Repos", profile.repo_count),
        ("Gists", profile.gists),
        ("Orgs", profile.orgs),
        ("Starred", profile.starred),
    )
    cell = INNER_WIDTH / len(row)
    for index, (label, value) in enumerate(row):
        x = CARD_PAD + cell * index + cell / 2
        canvas.add(
            el(
                "g",
                text(human(value), x, 294, 28, Color.TEXT, 800, "middle"),
                text(label, x, 318, 14, Color.MUTED, 500, "middle"),
                class_="rise",
                style=f"animation-delay:{0.3 + 0.06 * index:.2f}s",
            )
        )
    return canvas.render()


def render_stats(profile: Profile) -> str:
    tiles = (
        ("Contributions", profile.contributions, "active", Color.BLUE),
        ("Commits", profile.commits, "commits", Color.GREEN),
        ("Pull Requests", profile.pull_requests, "merged", Color.PURPLE),
        ("PRs Merged", profile.merged_prs, "veteran", Color.CYAN),
        ("Issues", profile.issues, "issues", Color.ORANGE),
        ("Code Reviews", profile.reviews, "reviews", Color.PINK),
        ("Repositories", profile.repo_count, "repos", Color.BLUE),
        ("Stars Earned", profile.stars, "stars", Color.YELLOW),
        ("Forks", profile.forks, "forks", Color.GREEN),
        ("Contributed To", profile.contributed_to, "explorer", Color.PURPLE),
        ("Starred Repos", profile.starred, "stars", Color.ORANGE),
        ("Public Gists", profile.gists, "languages", Color.RED),
    )
    columns, gap, tile_h, top = 4, 16, 104, 84
    tile_w = (INNER_WIDTH - gap * (columns - 1)) / columns
    rows = math.ceil(len(tiles) / columns)
    canvas = Canvas(CARD_WIDTH, top + rows * tile_h + (rows - 1) * gap + CARD_PAD, f"GitHub statistics for {profile.login}")
    frame(canvas, "GitHub Stats", f"@{profile.login} \u00b7 all-time")
    for index, (label, value, glyph, color) in enumerate(tiles):
        x = CARD_PAD + (index % columns) * (tile_w + gap)
        y = top + (index // columns) * (tile_h + gap)
        canvas.add(
            el(
                "g",
                el("rect", x=x, y=y, width=tile_w, height=tile_h, rx=14, fill=Color.PANEL, fill_opacity=0.9, stroke=Color.BORDER),
                el("circle", cx=x + tile_w - 32, cy=y + 32, r=20, fill=color, fill_opacity=0.12),
                icon(glyph, color, x + tile_w - 32, y + 32, 0.85),
                el("rect", x=x + 18, y=y + 18, width=28, height=4, rx=2, fill=color),
                text(human(value), x + 18, y + 68, 36, color, 800),
                text(label, x + 18, y + 90, 15, Color.MUTED, 500),
                class_="rise",
                style=f"animation-delay:{index * 0.06:.2f}s",
            )
        )
    return canvas.render()


def render_mix(profile: Profile) -> str:
    parts = (
        ("Commits", profile.commits, Color.GREEN),
        ("Pull Requests", profile.pull_requests, Color.PURPLE),
        ("Issues", profile.issues, Color.ORANGE),
        ("Code Reviews", profile.reviews, Color.PINK),
    )
    total = sum(value for _, value, _ in parts)
    canvas = Canvas(CARD_WIDTH, 322, "Contribution mix")
    frame(canvas, "Contribution Mix", "commits \u00b7 PRs \u00b7 issues \u00b7 reviews")
    cx, cy, radius = 176, 198, 76
    canvas.add(el("circle", cx=cx, cy=cy, r=radius, fill="none", stroke="#21262d", stroke_width=26))
    start = 0.0
    for index, (_, value, color) in enumerate(parts):
        share = value / total * 100 if total else 0.0
        if share > 0:
            length = max(share - 1.2, 0.4)
            canvas.add(
                el(
                    "circle",
                    cx=cx,
                    cy=cy,
                    r=radius,
                    fill="none",
                    stroke=color,
                    stroke_width=26,
                    pathLength=100,
                    stroke_dasharray=f"{length:.2f} {100 - length:.2f}",
                    stroke_dashoffset=-round(start, 2),
                    transform=f"rotate(-90 {cx} {cy})",
                    class_="seg",
                    style=f"animation-delay:{index * 0.15:.2f}s",
                )
            )
        start += share
    canvas.add(
        text(human(total), cx, cy + 8, 32, Color.TEXT, 800, "middle"),
        text("activities", cx, cy + 30, 14, Color.MUTED, 500, "middle"),
    )
    legend_x, legend_end = 340, CARD_WIDTH - CARD_PAD
    for index, (label, value, color) in enumerate(parts):
        y = 128 + index * 52
        share = value / total * 100 if total else 0.0
        canvas.add(
            el(
                "g",
                el("circle", cx=legend_x + 7, cy=y - 6, r=7, fill=color),
                text(label, legend_x + 26, y, 19, Color.TEXT, 600),
                text(f"{human(value)}  \u00b7  {share:.0f}%", legend_end, y, 17, Color.MUTED, 500, "end"),
                el("rect", x=legend_x, y=y + 12, width=legend_end - legend_x, height=6, rx=3, fill="#21262d"),
                el("rect", x=legend_x, y=y + 12, width=max((legend_end - legend_x) * share / 100, 6 if value else 0), height=6, rx=3, fill=color, class_="grow", style=f"animation-delay:{0.3 + index * 0.1:.2f}s"),
                class_="rise",
                style=f"animation-delay:{0.1 + index * 0.08:.2f}s",
            )
        )
    return canvas.render()


def render_achievements(profile: Profile) -> str:
    items = evaluate_achievements(profile)
    unlocked = sum(1 for item in items if item.tier)
    points = sum(item.tier for item in items)
    columns, cell_h, top = 4, 172, 76
    cell_w = INNER_WIDTH / columns
    rows = math.ceil(len(items) / columns)
    canvas = Canvas(CARD_WIDTH, top + rows * cell_h + 12, "Achievements")
    frame(canvas, "Achievements", f"{unlocked}/{len(items)} unlocked \u00b7 {points}/{4 * len(items)} tier points")
    for index, item in enumerate(items):
        cx = CARD_PAD + (index % columns) * cell_w + cell_w / 2
        y = top + (index // columns) * cell_h
        color = TIER_COLORS[item.tier]
        nxt = TIER_COLORS[min(item.tier + 1, 4)]
        hex_y = y + 46
        parts = []
        if item.tier:
            parts.append(el("circle", cx=cx, cy=hex_y, r=50, fill=color, fill_opacity=0.1))
        parts += [
            el("polygon", points=hexagon(cx, hex_y, 36), fill=color if item.tier else Color.PANEL, fill_opacity=0.16 if item.tier else 1, stroke=color, stroke_width=2.5 if item.tier else 1.5, stroke_dasharray=None if item.tier else "4 4", stroke_linejoin="round"),
            icon(item.icon, color if item.tier else "#6e7681", cx, hex_y, 1.25),
            text(item.title, cx, y + 108, 16, Color.TEXT, 700, "middle"),
            text(TIER_NAMES[item.tier] if item.tier else item.blurb, cx, y + 127, 13, color if item.tier else Color.MUTED, 600, "middle"),
            el("rect", x=cx - 56, y=y + 138, width=112, height=5, rx=2.5, fill="#21262d"),
            el("rect", x=cx - 56, y=y + 138, width=max(112 * item.progress, 5 if item.progress else 0), height=5, rx=2.5, fill=nxt if item.tier < 4 else color, class_="grow", style=f"animation-delay:{0.4 + index * 0.04:.2f}s"),
            text(f"{human(item.value)} / {human(item.target)}" if item.target else "MAX LEVEL", cx, y + 160, 12, Color.MUTED, 500, "middle"),
        ]
        canvas.add(el("g", *parts, class_="rise", style=f"animation-delay:{index * 0.05:.2f}s"))
    return canvas.render()


def hour_label(hour: int) -> str:
    return f"{hour % 12 or 12}{'a' if hour < 12 else 'p'}"


def window_color(hour: int) -> str:
    for (name, _, members), color in zip(WINDOWS, (Color.PURPLE, Color.CYAN, Color.BLUE, Color.PINK)):
        if hour in members:
            return color
    return Color.BLUE


def render_rhythm(profile: Profile) -> str:
    hours = hour_histogram(profile.commit_log)
    weekdays = weekday_histogram(profile.days)
    label, note, _ = chronotype(hours)
    canvas = Canvas(CARD_WIDTH, 580, "Coding rhythm")
    frame(canvas, "Coding Rhythm", f"UTC{UTC_OFFSET_HOURS:+g} \u00b7 {sum(hours)} commits analysed")
    canvas.define(linear("chrono-ink", stop(0, "#ffffff"), stop(60, "#a5d6ff"), stop(100, "#d2a8ff")))
    canvas.add(
        el("g", text(label, CARD_PAD, 122, 34, "url(#chrono-ink)", 800), text(note, CARD_PAD, 150, 16, Color.MUTED), class_="rise")
    )
    for index, ((name, span, _), color) in enumerate(zip(WINDOWS, (Color.PURPLE, Color.CYAN, Color.BLUE, Color.PINK))):
        x = CARD_PAD + index * 184
        canvas.add(el("circle", cx=x + 6, cy=186, r=5, fill=color), text(f"{name.split()[0]} {span}".replace(" \u2013 ", "\u2013"), x + 18, 191, 12.5, Color.MUTED, 500))
    chart_x, chart_w, baseline, chart_h = CARD_PAD + 8, INNER_WIDTH - 16, 350, 120
    canvas.add(*render_bars(hours, chart_x, baseline, chart_w, chart_h, [window_color(hour) for hour in range(24)], gap=5))
    bar_pitch = chart_w / 24
    for hour in (0, 6, 12, 18, 23):
        canvas.add(text(hour_label(hour), chart_x + hour * bar_pitch + bar_pitch / 2 - 2, baseline + 22, 12, Color.MUTED, 500, "middle"))
    if max(hours) > 0:
        peak = hours.index(max(hours))
        canvas.add(text(f"{hours[peak]} commits", chart_x + peak * bar_pitch + bar_pitch / 2 - 2, baseline - chart_h - 12, 12, Color.TEXT, 700, "middle"))
    canvas.add(text("Activity by weekday", CARD_PAD, 412, 17, Color.TEXT, 600))
    day_names = ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")
    week_base, week_h = 530, 72
    canvas.add(*render_bars(weekdays, chart_x, week_base, chart_w, week_h, [Color.BLUE if 0 < day < 6 else Color.PURPLE for day in range(7)], gap=14))
    day_pitch = chart_w / 7
    for index, name in enumerate(day_names):
        x = chart_x + index * day_pitch + (day_pitch - 14 / 7) / 2 - 2
        canvas.add(text(name, x, week_base + 24, 13, Color.MUTED, 500, "middle"))
        if weekdays[index]:
            bar_h = max(weekdays[index] / max(weekdays) * week_h, 5)
            canvas.add(text(human(weekdays[index]), x, week_base - bar_h - 8, 12, Color.TEXT, 600, "middle"))
    return canvas.render()


def render_codestats(profile: Profile, now: datetime) -> str:
    commits = profile.commit_log
    if not commits:
        canvas = Canvas(CARD_WIDTH, 170, "Code stats")
        frame(canvas, "Code Stats", "commit history")
        canvas.add(text("Line and commit stats appear after your first commits.", CARD_WIDTH / 2, 118, 18, Color.MUTED, 400, "middle"))
        return canvas.render()
    added, removed, files = code_totals(commits)
    tiles = (
        ("Lines Added", f"+{human(added)}", Color.GREEN),
        ("Lines Removed", f"\u2212{human(removed)}", Color.RED),
        ("Net Change", f"{added - removed:+,}", Color.BLUE),
        ("Commits Analysed", human(len(commits)), Color.PURPLE),
        ("Avg Lines / Commit", human(round((added + removed) / len(commits))), Color.ORANGE),
        ("Files Touched", human(files), Color.CYAN),
    )
    columns, gap, tile_h, top = 3, 16, 92, 84
    tile_w = (INNER_WIDTH - gap * (columns - 1)) / columns
    balance_y = top + 2 * tile_h + gap + 44
    list_y = balance_y + 66
    recent = commits[:5]
    canvas = Canvas(CARD_WIDTH, list_y + 30 + len(recent) * 54 + 20, "Code stats")
    frame(canvas, "Code Stats", f"last {len(commits)} commits across your repos")
    for index, (label, value, color) in enumerate(tiles):
        x = CARD_PAD + (index % columns) * (tile_w + gap)
        y = top + (index // columns) * (tile_h + gap)
        canvas.add(
            el(
                "g",
                el("rect", x=x, y=y, width=tile_w, height=tile_h, rx=14, fill=Color.PANEL, fill_opacity=0.9, stroke=Color.BORDER),
                el("rect", x=x + 18, y=y + 16, width=28, height=4, rx=2, fill=color),
                text(value, x + 18, y + 58, 32, color, 800),
                text(label, x + 18, y + 80, 15, Color.MUTED, 500),
                class_="rise",
                style=f"animation-delay:{index * 0.06:.2f}s",
            )
        )
    share = added / max(added + removed, 1)
    bar_w = INNER_WIDTH
    canvas.add(
        text("Added vs removed", CARD_PAD, balance_y, 15, Color.MUTED, 600),
        text(f"{share * 100:.0f}% / {100 - share * 100:.0f}%", CARD_WIDTH - CARD_PAD, balance_y, 15, Color.MUTED, 600, "end"),
        el("rect", x=CARD_PAD, y=balance_y + 12, width=bar_w, height=10, rx=5, fill=Color.RED, fill_opacity=0.85),
        el("rect", x=CARD_PAD, y=balance_y + 12, width=max(bar_w * share, 10), height=10, rx=5, fill=Color.GREEN, class_="grow", style="animation-delay:.5s"),
        text("Latest commits", CARD_PAD, list_y, 17, Color.TEXT, 600),
    )
    for index, commit in enumerate(recent):
        y = list_y + 18 + index * 54
        canvas.add(
            el(
                "g",
                el("rect", x=CARD_PAD, y=y, width=INNER_WIDTH, height=1, fill=Color.BORDER, fill_opacity=0.7),
                text(shorten(commit.message, 52, placeholder="\u2026"), CARD_PAD, y + 26, 17, Color.TEXT, 600),
                text(f"{commit.repo}  \u00b7  {ago(commit.when, now)}", CARD_PAD, y + 46, 13, Color.MUTED, 500),
                el("text", el("tspan", f"+{human(commit.additions)}", fill=Color.GREEN), el("tspan", f"  \u2212{human(commit.deletions)}", fill=Color.RED), x=CARD_WIDTH - CARD_PAD, y=y + 30, font_size=15, font_weight=700, text_anchor="end"),
                class_="rise",
                style=f"animation-delay:{0.3 + index * 0.07:.2f}s",
            )
        )
    return canvas.render()


def render_music(music: Music, now: datetime) -> str:
    accent = SPOTIFY_GREEN if music.source == "Spotify" else LASTFM_RED
    tracks = music.top_tracks
    show_popularity = any(track.popularity for track in tracks)
    top = 84
    tracks_y = top + 96 + 44
    artists_y = tracks_y + 24 + len(tracks) * 58 + 34
    genres_y = artists_y + 176
    genre_rows = len(music.genres)
    height = genres_y + (34 + genre_rows * 30 if genre_rows else 0) + 16
    canvas = Canvas(CARD_WIDTH, height, f"Music listening from {music.source}")
    frame(canvas, "Now Listening", f"{music.source} \u00b7 {music.period}")
    canvas.define(linear("music-accent", stop(0, accent), stop(100, Color.PURPLE), x1=0, y1=0, x2=0, y2=1))
    current = music.current
    if current:
        add_cover(canvas, "cover-now", CARD_PAD, top, 96, 14, current.cover, current.title[:1].upper(), (accent, Color.PURPLE))
        if current.playing:
            label = "NOW PLAYING"
            bars = [
                el("rect", x=CARD_PAD + 116 + index * 7, y=top + 6, width=4, height=14, rx=1.5, fill=accent, class_="eq", style=f"animation-delay:{index * 0.18:.2f}s")
                for index in range(4)
            ]
        else:
            label = f"LAST PLAYED \u00b7 {ago(current.when, now).upper()}" if current.when else "LAST PLAYED"
            bars = []
        text_x = CARD_PAD + 116 + (40 if bars else 0)
        canvas.add(
            el(
                "g",
                *bars,
                text(label, text_x if bars else CARD_PAD + 116, top + 18, 13, accent if current.playing else Color.MUTED, 700, letter_spacing=1.6),
                text(shorten(current.title, 28, placeholder="\u2026"), CARD_PAD + 116, top + 58, 26, Color.TEXT, 800),
                text(shorten(current.artist, 40, placeholder="\u2026"), CARD_PAD + 116, top + 86, 18, Color.MUTED, 500),
                class_="rise",
            )
        )
    for index, (label, value) in enumerate(music.stats[:2]):
        canvas.add(
            el(
                "g",
                text(value, CARD_WIDTH - CARD_PAD, top + 46 + index * 44, 22, Color.TEXT, 800, "end"),
                text(label, CARD_WIDTH - CARD_PAD, top + 62 + index * 44, 12, Color.MUTED, 500, "end"),
                class_="rise",
                style=f"animation-delay:{0.2 + index * 0.1:.2f}s",
            )
        )
    canvas.add(text(f"Top tracks \u00b7 {music.period}", CARD_PAD, tracks_y, 17, Color.TEXT, 600))
    for index, track in enumerate(tracks):
        y = tracks_y + 14 + index * 58
        add_cover(canvas, f"cover-t{index}", CARD_PAD + 34, y + 7, 44, 9, track.cover, track.title[:1].upper(), (Color.PANEL, "#2b3340"))
        right = []
        if show_popularity:
            right = [
                el("rect", x=CARD_WIDTH - CARD_PAD - 100, y=y + 24, width=100, height=6, rx=3, fill="#21262d"),
                el("rect", x=CARD_WIDTH - CARD_PAD - 100, y=y + 24, width=max(track.popularity, 4), height=6, rx=3, fill=accent, class_="grow", style=f"animation-delay:{0.4 + index * 0.08:.2f}s"),
            ]
        elif track.plays:
            right = [text(f"{track.plays:,} plays", CARD_WIDTH - CARD_PAD, y + 34, 15, Color.MUTED, 600, "end")]
        canvas.add(
            el(
                "g",
                el("rect", x=CARD_PAD, y=y, width=INNER_WIDTH, height=1, fill=Color.BORDER, fill_opacity=0.7),
                text(f"{index + 1}", CARD_PAD + 8, y + 34, 17, accent, 800),
                text(shorten(track.title, 40, placeholder="\u2026"), CARD_PAD + 92, y + 27, 17, Color.TEXT, 700),
                text(shorten(track.artist, 44, placeholder="\u2026"), CARD_PAD + 92, y + 46, 14, Color.MUTED, 500),
                *right,
                class_="rise",
                style=f"animation-delay:{0.15 + index * 0.07:.2f}s",
            )
        )
    canvas.add(text(f"Top artists \u00b7 {music.period}", CARD_PAD, artists_y, 17, Color.TEXT, 600))
    cell = INNER_WIDTH / 5
    for index, artist in enumerate(music.top_artists[:5]):
        cx = CARD_PAD + cell * index + cell / 2
        add_cover(canvas, f"cover-a{index}", cx - 34, artists_y + 16, 68, 34, artist.image, artist.name[:1].upper(), (accent, Color.PURPLE))
        sub = artist.tags[0] if artist.tags else (f"{artist.plays:,} plays" if artist.plays else "")
        canvas.add(
            el(
                "g",
                text(shorten(artist.name, 15, placeholder="\u2026"), cx, artists_y + 106, 15, Color.TEXT, 700, "middle"),
                text(shorten(sub, 18, placeholder="\u2026"), cx, artists_y + 126, 12, Color.MUTED, 500, "middle"),
                class_="rise",
                style=f"animation-delay:{0.2 + index * 0.08:.2f}s",
            )
        )
    if music.genres:
        canvas.add(text("Top genres", CARD_PAD, genres_y, 17, Color.TEXT, 600))
        peak = max(count for _, count in music.genres)
        for index, (genre, count) in enumerate(music.genres):
            y = genres_y + 34 + index * 30
            width = 380 * count / peak
            canvas.add(
                el(
                    "g",
                    text(shorten(genre.title(), 24, placeholder="\u2026"), CARD_PAD, y, 15, Color.TEXT, 500),
                    el("rect", x=280, y=y - 11, width=460, height=12, rx=6, fill="#21262d"),
                    el("rect", x=280, y=y - 11, width=max(width * 460 / 380, 12), height=12, rx=6, fill="url(#music-accent)", class_="grow", style=f"animation-delay:{0.3 + index * 0.08:.2f}s"),
                    class_="rise",
                )
            )
    return canvas.render()


def render_wakatime(waka: Waka) -> str:
    tiles = (("Last 7 Days", waka.total, Color.BLUE), ("Daily Average", waka.daily_average, Color.PURPLE), ("All Time", waka.all_time, Color.GREEN))
    gap, tile_h, top = 16, 96, 84
    tile_w = (INNER_WIDTH - gap * 2) / 3
    languages_y = top + tile_h + 78
    languages = waka.languages
    lower_y = languages_y + 22 + len(languages) * 36 + 26
    lower_rows = max(len(waka.editors), len(waka.systems), 1)
    height = lower_y + 30 + lower_rows * 30 + 12
    canvas = Canvas(CARD_WIDTH, height, "WakaTime coding activity")
    frame(canvas, "Coding Time", "WakaTime \u00b7 last 7 days")
    for index, (label, value, color) in enumerate(tiles):
        x = CARD_PAD + index * (tile_w + gap)
        canvas.add(
            el(
                "g",
                el("rect", x=x, y=top, width=tile_w, height=tile_h, rx=14, fill=Color.PANEL, fill_opacity=0.9, stroke=Color.BORDER),
                el("rect", x=x + 18, y=top + 16, width=28, height=4, rx=2, fill=color),
                text(shorten(value, 16, placeholder="\u2026"), x + 18, top + 58, 24, color, 800),
                text(label, x + 18, top + 80, 15, Color.MUTED, 500),
                class_="rise",
                style=f"animation-delay:{index * 0.08:.2f}s",
            )
        )
    canvas.add(text(f"Best day  \u00b7  {waka.best_day}", CARD_PAD, top + tile_h + 34, 15, Color.MUTED, 600), text("Languages", CARD_PAD, languages_y, 17, Color.TEXT, 600))
    for index, (name, percent, label) in enumerate(languages):
        y = languages_y + 34 + index * 36
        color = PALETTE[index % len(PALETTE)]
        canvas.add(
            el(
                "g",
                text(shorten(name, 14, placeholder="\u2026"), CARD_PAD, y, 16, Color.TEXT, 600),
                el("rect", x=170, y=y - 12, width=400, height=12, rx=6, fill="#21262d"),
                el("rect", x=170, y=y - 12, width=max(400 * percent / 100, 12), height=12, rx=6, fill=color, class_="grow", style=f"animation-delay:{0.3 + index * 0.08:.2f}s"),
                text(f"{percent:.1f}%  \u00b7  {label}" if label else f"{percent:.1f}%", CARD_WIDTH - CARD_PAD, y, 14, Color.MUTED, 500, "end"),
                class_="rise",
                style=f"animation-delay:{0.1 + index * 0.06:.2f}s",
            )
        )
    column_w = (INNER_WIDTH - 24) / 2
    for column, (heading, rows) in enumerate((("Editors", waka.editors), ("Operating systems", waka.systems))):
        x = CARD_PAD + column * (column_w + 24)
        canvas.add(text(heading, x, lower_y, 17, Color.TEXT, 600))
        for index, (name, percent, _) in enumerate(rows):
            y = lower_y + 30 + index * 30
            canvas.add(
                el("circle", cx=x + 6, cy=y - 5, r=5, fill=PALETTE[(index + column * 2) % len(PALETTE)]),
                text(shorten(name, 22, placeholder="\u2026"), x + 20, y, 15, Color.TEXT, 500),
                text(f"{percent:.1f}%", x + column_w, y, 14, Color.MUTED, 500, "end"),
            )
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


def build_assets(profile: Profile, identity: Identity, music: Music | None = None, waka: Waka | None = None, now: datetime | None = None) -> dict[str, str | None]:
    now = now or datetime.now(timezone.utc)
    return {
        "header.svg": render_header(identity),
        "typing.svg": render_typing(identity),
        "about.svg": render_about(identity),
        "profile.svg": render_profile(profile, identity),
        "stats.svg": render_stats(profile),
        "mix.svg": render_mix(profile),
        "achievements.svg": render_achievements(profile),
        "streak.svg": render_streak(profile),
        "languages.svg": render_languages(profile),
        "codestats.svg": render_codestats(profile, now),
        "rhythm.svg": render_rhythm(profile),
        "activity.svg": render_activity(profile),
        "music.svg": render_music(music, now) if music else None,
        "wakatime.svg": render_wakatime(waka) if waka else None,
        "projects.svg": render_projects(profile),
        "divider.svg": render_divider(),
        "footer.svg": render_footer(identity, profile.today),
    }


def write_assets(assets: dict[str, str | None], directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, content in assets.items():
        target = directory / name
        if content is None:
            if target.exists():
                print(f"{name:<18}kept previous version")
                continue
            content = BLANK_SVG
        if not target.exists() or target.read_text(encoding="utf-8") != content:
            target.write_text(content, encoding="utf-8")
        print(f"{name:<18}{len(content.encode('utf-8')):>8} bytes")


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
    assets = build_assets(profile, IDENTITY, load_music(), load_waka(profile.today))
    write_assets(assets, ASSETS_DIR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
