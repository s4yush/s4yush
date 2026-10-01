"""
config.py -- the single place every script reads environment variables and
secrets from. Nothing else in this project should call os.environ.get()
directly; it should import a *Config object from here instead.

You never edit VALUES in this file. Secret values live in:
  GitHub repo -> Settings -> Secrets and variables -> Actions

This file only defines which NAMES each script looks for, sane defaults,
and whether each integration is "configured" (all of its keys present).

--------------------------------------------------------------------------
Required for the profile to build at all
--------------------------------------------------------------------------
  GITHUB_TOKEN    auto-provided by Actions as secrets.GITHUB_TOKEN
  PROFILE_LOGIN   optional -- defaults to the repo owner, no secret needed

--------------------------------------------------------------------------
Optional integrations -- each only turns on when ALL of its keys are set
--------------------------------------------------------------------------
  Spotify (now playing)      SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET,
                              SPOTIFY_REFRESH_TOKEN
                              (get these by running scripts/spotify_auth.py)
  Last.fm (fallback)         LASTFM_API_KEY, LASTFM_USERNAME
  WakaTime (coding activity) WAKATIME_API_KEY
  Cloudflare (views counter  CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID
  + live IST clock)
  content.json (profile      PROFILE_CONTENT_FILE -- optional override,
  data: skills/timeline/     defaults to <repo root>/content.json
  certificates/etc.)
--------------------------------------------------------------------------

Run this file directly to print a status report:
    python3 scripts/config.py
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


# ---------------------------------------------------------------------------
# GitHub -- required. Powers every stats card (commits, streaks, languages,
# activity, projects, etc).
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class GitHubConfig:
    token: str = field(default_factory=lambda: _env("GITHUB_TOKEN"))
    login: str = field(
        default_factory=lambda: _env("PROFILE_LOGIN") or _env("GITHUB_REPOSITORY_OWNER")
    )

    @property
    def configured(self) -> bool:
        return bool(self.token and self.login)


# ---------------------------------------------------------------------------
# Spotify -- optional. Powers the "now playing / recently played" card.
# Run `python3 scripts/spotify_auth.py` once to get SPOTIFY_REFRESH_TOKEN.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SpotifyConfig:
    client_id: str = field(default_factory=lambda: _env("SPOTIFY_CLIENT_ID"))
    client_secret: str = field(default_factory=lambda: _env("SPOTIFY_CLIENT_SECRET"))
    refresh_token: str = field(default_factory=lambda: _env("SPOTIFY_REFRESH_TOKEN"))
    redirect_uri: str = "http://127.0.0.1:8888/callback"
    scopes: str = "user-read-recently-played user-top-read user-read-currently-playing"

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.refresh_token)

    def as_tuple(self) -> tuple[str, str, str]:
        """Matches the (client_id, client_secret, refresh_token) order SpotifyClient expects."""
        return (self.client_id, self.client_secret, self.refresh_token)


# ---------------------------------------------------------------------------
# Last.fm -- optional. Used as the now-playing source when Spotify isn't set.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class LastFmConfig:
    api_key: str = field(default_factory=lambda: _env("LASTFM_API_KEY"))
    username: str = field(default_factory=lambda: _env("LASTFM_USERNAME"))

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.username)

    def as_tuple(self) -> tuple[str, str]:
        return (self.api_key, self.username)


# ---------------------------------------------------------------------------
# WakaTime -- optional. Powers the coding-activity / rhythm cards.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class WakaTimeConfig:
    api_key: str = field(default_factory=lambda: _env("WAKATIME_API_KEY"))

    @property
    def configured(self) -> bool:
        return bool(self.api_key)


# ---------------------------------------------------------------------------
# Cloudflare -- optional. Powers the views counter AND the live IST clock
# (both are routes on the same Worker).
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CloudflareConfig:
    api_token: str = field(default_factory=lambda: _env("CLOUDFLARE_API_TOKEN"))
    account_id: str = field(default_factory=lambda: _env("CLOUDFLARE_ACCOUNT_ID"))
    worker_name: str = "profile-views"
    namespace_title: str = "profile-views"
    placeholder_host: str = "YOUR-WORKER.workers.dev"

    @property
    def configured(self) -> bool:
        return bool(self.api_token and self.account_id)


# ---------------------------------------------------------------------------
# Content -- the content.json file that drives skills / timeline /
# certificates / taglines / etc. Always "configured" since it falls back
# to the built-in defaults in build_assets.py when missing.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ContentConfig:
    path: Path = field(
        default_factory=lambda: Path(_env("PROFILE_CONTENT_FILE") or str(ROOT / "content.json"))
    )

    @property
    def configured(self) -> bool:
        return self.path.exists()


# Single shared instance of each -- import these, don't re-instantiate.
GITHUB = GitHubConfig()
SPOTIFY = SpotifyConfig()
LASTFM = LastFmConfig()
WAKATIME = WakaTimeConfig()
CLOUDFLARE = CloudflareConfig()
CONTENT = ContentConfig()


def summary() -> str:
    rows = [
        ("GitHub API", GITHUB.configured, "required"),
        ("content.json", CONTENT.configured, "optional, falls back to built-in defaults"),
        ("Spotify", SPOTIFY.configured, "optional, now-playing card"),
        ("Last.fm", LASTFM.configured, "optional, now-playing fallback"),
        ("WakaTime", WAKATIME.configured, "optional, coding-activity card"),
        ("Cloudflare", CLOUDFLARE.configured, "optional, views counter + live clock"),
    ]
    width = max(len(name) for name, *_ in rows)
    lines = ["Profile config:"]
    for name, ok, note in rows:
        mark = "\u2714" if ok else "\u00b7"
        lines.append(f"  {mark} {name.ljust(width)}  {note}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(summary())
    if not GITHUB.configured:
        print("\nMissing required GITHUB_TOKEN / PROFILE_LOGIN.", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)
