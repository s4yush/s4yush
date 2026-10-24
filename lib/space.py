from __future__ import annotations

import json
import os
import random
import sys
import urllib.error
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import build_assets as ba
import config
import extra_cards as extra
from build_assets import Color, el

LOOP = 20
QUERY = "query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}"


def fetch_days(token: str, login: str) -> tuple[ba.Day, ...]:
    data = ba.GitHubClient(token).execute(QUERY, {"login": login})
    weeks = data["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return tuple(ba.Day(date.fromisoformat(d["date"]), d["contributionCount"]) for w in weeks for d in w["contributionDays"])


def render_space(days: tuple[ba.Day, ...], today: date, login: str) -> str:
    start, weeks = ba.activity_window(days, today)
    counts = {d.when: d.count for d in days}
    visible = [start + timedelta(days=i) for i in range(weeks * 7) if start + timedelta(days=i) <= today]
    peak = max((counts.get(d, 0) for d in visible), default=0)
    total = sum(counts.get(d, 0) for d in visible)
    pitch = min(14, ba.INNER_WIDTH // weeks)
    cell = pitch - 3
    grid_w, grid_h = weeks * pitch - 3, 7 * pitch - 3
    gx, gy = (ba.CARD_WIDTH - grid_w) / 2, 104
    ship_y = gy + grid_h + 46
    when = lambda c: 3 + 85 * (c + 0.5) / weeks
    x0, x1 = gx + cell / 2, gx + (weeks - 1) * pitch + cell / 2

    canvas = ba.Canvas(ba.CARD_WIDTH, ship_y + 42, f"Contribution space defense for {login}: {total} contributions")
    ba.frame(canvas, "Space Defense", f"{total:,} contributions · last {weeks} weeks")

    columns = sorted({(d - start).days // 7 for d in visible if counts.get(d, 0)})
    zap = "".join(f"{when(c) - 0.5:.2f}%{{opacity:0}}{when(c):.2f}%{{opacity:1}}{when(c) + 0.7:.2f}%{{opacity:0}}" for c in range(weeks))
    canvas.style(
        ".c{transform-box:fill-box;transform-origin:center}",
        f".ship{{animation:fly {LOOP}s linear infinite}}",
        f".zap{{animation:zap {LOOP}s linear infinite}}",
        f"@keyframes fly{{0%,{when(0):.2f}%{{transform:translateX({x0:.1f}px)}}{when(weeks - 1):.2f}%,100%{{transform:translateX({x1:.1f}px)}}}}",
        f"@keyframes zap{{0%{{opacity:0}}{zap}100%{{opacity:0}}}}",
        *[f".k{c}{{animation:k{c} {LOOP}s linear infinite}}" for c in columns],
        *[
            f"@keyframes k{c}{{0%,{when(c):.2f}%{{opacity:1;transform:scale(1)}}{when(c) + 1.2:.2f}%{{opacity:1;transform:scale(1.8)}}"
            f"{when(c) + 3:.2f}%,98%{{opacity:0;transform:scale(0)}}100%{{opacity:1;transform:scale(1)}}}}"
            for c in columns
        ],
    )
    canvas.define(
        el("pattern", el("rect", width=cell, height=cell, rx=2.5, fill="#ffffff", fill_opacity=0.05), id="slot", width=pitch, height=pitch, x=gx, y=gy, patternUnits="userSpaceOnUse"),
        ba.linear("beam", ba.stop(0, Color.CYAN, 0), ba.stop(100, "#ffffff", 1), x2=0, y2=1),
        ba.linear("hull", ba.stop(0, "#ffffff"), ba.stop(100, "#aab6d8"), x2=0, y2=1),
    )

    rng = random.Random(7)
    stars = [el("circle", cx=rng.randint(20, 780), cy=rng.randint(70, int(ship_y + 30)), r=round(rng.uniform(0.6, 1.4), 1), fill="#ffffff", opacity=round(rng.uniform(0.3, 0.7), 1)) for _ in range(28)]
    cells = [
        el("rect", x=gx + (d - start).days // 7 * pitch, y=gy + (d - start).days % 7 * pitch, width=cell, height=cell, rx=2.5, fill=Color.HEAT[ba.heat_level(counts[d], peak)], class_=f"c k{(d - start).days // 7}")
        for d in visible
        if counts.get(d, 0)
    ]
    rocket = [
        el("rect", x=-1.6, y=-(ship_y - gy + 4), width=3.2, height=ship_y - gy, fill="url(#beam)", class_="zap"),
        el("path", d="M-3,11 Q0,26 3,11Z", fill=Color.ORANGE, class_="flicker"),
        el("path", d="M-4,5 L-10,14 L-4,11Z M4,5 L10,14 L4,11Z", fill=Color.PINK),
        el("path", d="M0,-16 C7,-8 7,4 4,11 H-4 C-7,4 -7,-8 0,-16Z", fill="url(#hull)"),
        el("circle", cy=-4, r=2.6, fill=Color.CYAN),
    ]
    canvas.add(
        el("g", *stars, class_="twinkle"),
        ba.text(f"{total:,} contributions detected — rocket is clearing them all", ba.CARD_PAD, 80, 15, Color.MUTED, class_="pulse"),
        el("rect", x=gx, y=gy, width=grid_w, height=grid_h, fill="url(#slot)"),
        *cells,
        el("g", el("g", *rocket, class_="ship"), transform=f"translate(0 {ba.num(ship_y)})"),
    )
    return canvas.render()


def total_views(store: Path, repo: str, token: str) -> int | None:
    seen = json.loads(store.read_text()) if store.exists() else {}
    try:
        data = ba.http_json(f"https://api.github.com/repos/{repo}/traffic/views", {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "User-Agent": "profile-assets-builder"})
    except urllib.error.HTTPError as error:
        print(f"Traffic API HTTP {error.code}: PROFILE_TOKEN (classic PAT, repo scope) is required", file=sys.stderr)
        data = None
    for day in (data or {}).get("views", []):
        seen[day["timestamp"][:10]] = day["count"]
    if data is None and not seen:
        try:
            return extra.fetch_count(repo.split("/")[0])
        except Exception as error:
            print(f"Counter fallback failed: {error}", file=sys.stderr)
            return None
    store.write_text(json.dumps(seen, sort_keys=True))
    return sum(seen.values()) + int(os.environ.get("VIEWS_BASE", 0))


def main() -> int:
    if not config.GITHUB.configured:
        print("GITHUB_TOKEN and PROFILE_LOGIN must be set", file=sys.stderr)
        return 2
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "out")
    out.mkdir(parents=True, exist_ok=True)
    token, login = config.GITHUB.token, config.GITHUB.login
    today = datetime.now(timezone.utc).date()
    (out / "space.svg").write_text(render_space(fetch_days(token, login), today, login), encoding="utf-8")
    repo = os.environ.get("GITHUB_REPOSITORY", f"{login}/{login}")
    views = total_views(out / "views.json", repo, token)
    if views is not None:
        (out / "views.svg").write_text(extra.render_views(views, login), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
    
