import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


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
        return (os.environ.get("PROFILE_LOGIN") or "s4yush").strip()

    @property
    def configured(self) -> bool:
        return bool(self.token)


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
