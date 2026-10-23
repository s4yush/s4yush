import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


LOGIN_PATTERN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})")


class Provider:
    def __init__(self, *names: str) -> None:
        self.names = names

    def values(self) -> tuple[str, ...]:
        return tuple(os.environ.get(name, "").strip() for name in self.names)

    @property
    def configured(self) -> bool:
        return all(self.values())

    def as_tuple(self) -> tuple[str, ...]:
        return self.values()

    @property
    def api_key(self) -> str:
        return self.values()[0]


class GitHub:
    @property
    def token(self) -> str:
        return (os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or "").strip()

    @property
    def login(self) -> str:
        return (os.environ.get("PROFILE_LOGIN") or os.environ.get("GITHUB_REPOSITORY_OWNER") or "s4yush").strip()

    @property
    def configured(self) -> bool:
        return bool(self.token) and LOGIN_PATTERN.fullmatch(self.login) is not None


class Content:
    path = next(
        (candidate for candidate in (ROOT / "content.json", ROOT / "lib" / "content.json") if candidate.exists()),
        ROOT / "content.json",
    )


SPOTIFY = Provider("SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET", "SPOTIFY_REFRESH_TOKEN")
LASTFM = Provider("LASTFM_API_KEY", "LASTFM_USERNAME")
WAKATIME = Provider("WAKATIME_API_KEY")
GITHUB = GitHub()
CONTENT = Content()


def summary() -> str:
    def state(flag: bool) -> str:
        return "set" if flag else "missing"

    rows = (
        ("GitHub token", state(bool(GITHUB.token))),
        ("GitHub login", GITHUB.login if LOGIN_PATTERN.fullmatch(GITHUB.login) else "invalid"),
        ("Spotify", state(SPOTIFY.configured)),
        ("Last.fm", state(LASTFM.configured)),
        ("WakaTime", state(WAKATIME.configured)),
        ("content.json", state(CONTENT.path.exists())),
    )
    return "\n".join(f"{label:<14}{value}" for label, value in rows)
