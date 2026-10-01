import datetime
import json
import math
import os
import random
import sys
import urllib.request
from pathlib import Path

import ui
from ui import T, esc, fmt, window, reveal

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "generated"

QUERY = """
query($login:String!){
  user(login:$login){
    followers{totalCount}
    pullRequests{totalCount}
    issues{totalCount}
    repositories(ownerAffiliation:OWNER,isFork:false,privacy:PUBLIC,first:100,orderBy:{field:PUSHED_AT,direction:DESC}){
      totalCount
      nodes{
        name description url stargazerCount pushedAt
        primaryLanguage{name color}
        languages(first:8,orderBy:{field:SIZE,direction:DESC}){edges{size node{name color}}}
      }
    }
    contributionsCollection{
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalPullRequestReviewContributions
      contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}
    }
  }
}
"""

FALLBACK = ["#5eead4", "#a78bfa", "#7aa2f7", "#f9a8d4", "#fcd34d", "#86efac", "#fdba74"]


def load_cfg():
    return json.loads((ROOT / "config.json").read_text(encoding="utf-8"))


def fetch(login, token):
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "profile-readme"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)
    if data.get("errors"):
        raise RuntimeError(data["errors"])
    return data["data"]["user"]


def demo(login):
    rnd = random.Random(7)
    today = datetime.date.today()
    start = today - datetime.timedelta(days=364)
    start -= datetime.timedelta(days=(start.weekday() + 1) % 7)
    days = []
    d = start
    while d <= today:
        v = rnd.choice([0, 0, 0, 1, 2, 3, 5, 8]) if rnd.random() > 0.3 else 0
        days.append({"date": d.isoformat(), "contributionCount": v})
        d += datetime.timedelta(days=1)
    weeks = [{"contributionDays": days[i:i + 7]} for i in range(0, len(days), 7)]
    repos = [
        {"name": "telegram-bot-kit", "description": "Reusable building blocks for fast Telegram bots", "url": "", "stargazerCount": 12, "pushedAt": "2026-09-20T00:00:00Z", "primaryLanguage": {"name": "Python", "color": "#3572A5"}, "languages": {"edges": [{"size": 90000, "node": {"name": "Python", "color": "#3572A5"}}, {"size": 12000, "node": {"name": "Shell", "color": "#89e051"}}]}},
        {"name": "c-compiler", "description": "A small C compiler built from scratch", "url": "", "stargazerCount": 7, "pushedAt": "2026-09-10T00:00:00Z", "primaryLanguage": {"name": "C", "color": "#555555"}, "languages": {"edges": [{"size": 60000, "node": {"name": "C", "color": "#555555"}}]}},
        {"name": "api-playground", "description": "FastAPI + MongoDB starter with auth and rate limits", "url": "", "stargazerCount": 4, "pushedAt": "2026-08-30T00:00:00Z", "primaryLanguage": {"name": "Python", "color": "#3572A5"}, "languages": {"edges": [{"size": 30000, "node": {"name": "Python", "color": "#3572A5"}}, {"size": 8000, "node": {"name": "JavaScript", "color": "#f1e05a"}}]}},
        {"name": "web-portfolio", "description": "Personal site with motion and 3D", "url": "", "stargazerCount": 2, "pushedAt": "2026-08-01T00:00:00Z", "primaryLanguage": {"name": "TypeScript", "color": "#3178c6"}, "languages": {"edges": [{"size": 25000, "node": {"name": "TypeScript", "color": "#3178c6"}}, {"size": 6000, "node": {"name": "CSS", "color": "#563d7c"}}]}},
    ]
    total = sum(x["contributionCount"] for x in days)
    return {
        "followers": {"totalCount": 0},
        "pullRequests": {"totalCount": 0},
        "issues": {"totalCount": 0},
        "repositories": {"totalCount": len(repos), "nodes": repos},
        "contributionsCollection": {
            "totalCommitContributions": total,
            "totalPullRequestContributions": 0,
            "totalIssueContributions": 0,
            "totalPullRequestReviewContributions": 0,
            "contributionCalendar": {"totalContributions": total, "weeks": weeks},
        },
    }


def streaks(days):
    counts = [c for _, c in days]
    longest = run = 0
    for c in counts:
        run = run + 1 if c > 0 else 0
        longest = max(longest, run)
    i = len(counts) - 1
    if i >= 0 and counts[i] == 0:
        i -= 1
    cur = 0
    while i >= 0 and counts[i] > 0:
        cur += 1
        i -= 1
    return cur, longest


def normalize(u, cfg):
    login = cfg["login"]
    skip_repos = set(cfg.get("exclude_repos", [])) | {login}
    skip_langs = set(cfg.get("exclude_languages", []))
    repos = [r for r in u["repositories"]["nodes"] if r["name"] not in skip_repos]
    langs = {}
    for r in repos:
        for e in r["languages"]["edges"]:
            n = e["node"]["name"]
            if n in skip_langs:
                continue
            slot = langs.setdefault(n, [e["node"]["color"] or "#8b98b3", 0])
            slot[1] += e["size"]
    lang_list = sorted(((n, c, s) for n, (c, s) in langs.items()), key=lambda x: -x[2])
    cc = u["contributionsCollection"]
    cal = cc["contributionCalendar"]
    days = [(x["date"], x["contributionCount"]) for w in cal["weeks"] for x in w["contributionDays"]]
    cur, longest = streaks(days)
    projects = sorted(repos, key=lambda r: (r["stargazerCount"], r["pushedAt"]), reverse=True)[: cfg.get("projects", 4)]
    return {
        "commits": cc["totalCommitContributions"],
        "prs": cc["totalPullRequestContributions"],
        "issues": cc["totalIssueContributions"],
        "reviews": cc["totalPullRequestReviewContributions"],
        "stars": sum(r["stargazerCount"] for r in repos),
        "repos": len(repos),
        "followers": u["followers"]["totalCount"],
        "total": cal["totalContributions"],
        "weeks": cal["weeks"],
        "streak": cur,
        "longest": longest,
        "langs": lang_list,
        "projects": projects,
    }


def stats_card(d):
    w, h, u = 450, 330, "s"
    rows = [
        ("commits", d["commits"]),
        ("pull requests", d["prs"]),
        ("issues", d["issues"]),
        ("reviews", d["reviews"]),
        ("stars earned", d["stars"]),
        ("public repos", d["repos"]),
        ("followers", d["followers"]),
    ]
    b = []
    for i, (k, v) in enumerate(rows):
        y = 92 + i * 28
        c = (
            f'<text x="44" y="{y}" font-size="13" fill="{T["muted"]}">{esc(k)}</text>'
            f'<text x="262" y="{y}" font-size="14" font-weight="700" text-anchor="end" fill="{T["text"]}">{fmt(v)}</text>'
            f'<line x1="44" y1="{y + 8}" x2="262" y2="{y + 8}" stroke="#1c2a47" stroke-dasharray="2 4"/>'
        )
        b.append(reveal(c, 0.3 + i * 0.12))
    r = 46
    circ = 2 * math.pi * r
    p = min(d["streak"] / max(d["longest"], 1), 1)
    off = circ * (1 - p)
    b.append(
        f'<g transform="translate(352 142) rotate(-90)">'
        f'<circle r="{r}" fill="none" stroke="#1c2a47" stroke-width="8"/>'
        f'<circle r="{r}" fill="none" stroke="url(#tg{u})" stroke-width="8" stroke-linecap="round" stroke-dasharray="{circ:.2f}" stroke-dashoffset="{circ:.2f}">'
        f'<animate attributeName="stroke-dashoffset" from="{circ:.2f}" to="{off:.2f}" dur="1.6s" begin=".6s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".2 .7 .2 1"/></circle></g>'
        f'<text x="352" y="150" text-anchor="middle" font-size="26" font-weight="800" fill="{T["text"]}">{fmt(d["streak"])}</text>'
        f'<text x="352" y="170" text-anchor="middle" font-size="10" fill="{T["muted"]}">day streak</text>'
        f'<text x="352" y="224" text-anchor="middle" font-size="12" fill="{T["muted"]}">longest</text>'
        f'<text x="352" y="244" text-anchor="middle" font-size="15" font-weight="700" fill="{T["a1"]}">{fmt(d["longest"])} days</text>'
        f'<text x="352" y="268" text-anchor="middle" font-size="12" fill="{T["muted"]}">last year</text>'
        f'<text x="352" y="288" text-anchor="middle" font-size="15" font-weight="700" fill="{T["a2"]}">{fmt(d["total"])}</text>'
    )
    return window(w, h, "stats.sh", "".join(b), u)


def langs_card(d):
    w, h, u = 450, 330, "l"
    items = d["langs"][:6]
    total = sum(s for _, _, s in items) or 1
    bw = 362
    b = []
    if not items:
        b.append(f'<text x="44" y="100" font-size="13" fill="{T["muted"]}">no language data yet</text>')
    for i, (name, color, size) in enumerate(items):
        pct = size / total * 100
        y = 92 + i * 34
        c = color if color and color.startswith("#") else FALLBACK[i % len(FALLBACK)]
        fw = max(pct / 100 * bw, 3)
        b.append(
            f'<text x="44" y="{y}" font-size="13" fill="{T["text"]}">{esc(name)}</text>'
            f'<text x="406" y="{y}" font-size="12" text-anchor="end" fill="{T["muted"]}">{pct:.1f}%</text>'
            f'<rect x="44" y="{y + 8}" width="{bw}" height="8" rx="4" fill="#16213a"/>'
            f'<rect x="44" y="{y + 8}" width="0" height="8" rx="4" fill="{c}">'
            f'<animate attributeName="width" from="0" to="{fw:.1f}" dur="1.1s" begin="{0.4 + i * 0.15:.2f}s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".2 .7 .2 1"/></rect>'
        )
    return window(w, h, "languages.sh", "".join(b), u)


def contrib_card(d):
    w, h, u = 900, 270, "c"
    levels = ["#141d33", "#164e63", "#0f766e", "#14b8a6", T["a1"]]
    allc = [x["contributionCount"] for wk in d["weeks"] for x in wk["contributionDays"]]
    mx = max(allc + [1])
    x0, y0, pitch = 66, 92, 15
    b = []
    last_month = None
    for wi, wk in enumerate(d["weeks"]):
        for day in wk["contributionDays"]:
            dt = datetime.date.fromisoformat(day["date"])
            row = (dt.weekday() + 1) % 7
            c = day["contributionCount"]
            if row == 0 or day is wk["contributionDays"][0]:
                if dt.month != last_month and wi < len(d["weeks"]) - 2:
                    b.append(f'<text x="{x0 + wi * pitch}" y="80" font-size="10" fill="{T["muted"]}">{dt.strftime("%b")}</text>')
                    last_month = dt.month
            lvl = 0 if c == 0 else min(4, 1 + int(c / mx * 3.999))
            x = x0 + wi * pitch
            y = y0 + row * pitch
            begin = 0.3 + wi * 0.03 + row * 0.01
            extra = ""
            if lvl >= 3:
                extra = f'<animate attributeName="opacity" values="1;.5;1" dur="4s" begin="{begin + 2 + wi * 0.05:.2f}s" repeatCount="indefinite"/>'
            b.append(
                f'<rect x="{x}" y="{y}" width="12" height="12" rx="3" fill="{levels[lvl]}" opacity="0">'
                f'<animate attributeName="opacity" from="0" to="1" dur=".35s" begin="{begin:.2f}s" fill="freeze"/>{extra}</rect>'
            )
    for r, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        b.append(f'<text x="34" y="{y0 + r * pitch + 10}" font-size="10" fill="{T["muted"]}">{name}</text>')
    lx = 660
    b.append(f'<text x="{lx - 34}" y="226" font-size="10" fill="{T["muted"]}">less</text>')
    for i, c in enumerate(levels):
        b.append(f'<rect x="{lx + i * 17}" y="216" width="12" height="12" rx="3" fill="{c}"/>')
    b.append(f'<text x="{lx + 5 * 17 + 6}" y="226" font-size="10" fill="{T["muted"]}">more</text>')
    b.append(f'<text x="66" y="226" font-size="12" fill="{T["text"]}">{fmt(d["total"])} contributions in the last year</text>')
    return window(w, h, "contributions.sh", "".join(b), u)


def cut(s, n):
    s = (s or "no description").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def projects_card(d):
    w, u = 900, "p"
    items = d["projects"]
    h = max(190, 112 + len(items) * 52)
    b = [f'<text x="52" y="82" font-size="13" fill="{T["muted"]}">s4yush@mac ~ % ls -la ~/projects</text>']
    for i, r in enumerate(items):
        y = 116 + i * 52
        lang = r["primaryLanguage"] or {"name": "—", "color": "#8b98b3"}
        c = (
            f'<rect x="44" y="{y - 22}" width="{w - 88}" height="44" rx="10" fill="#fff" fill-opacity=".03" stroke="#fff" stroke-opacity=".06"/>'
            f'<text x="62" y="{y - 2}" font-size="15" font-weight="700" fill="{T["a1"]}">▸ {esc(r["name"])}</text>'
            f'<text x="62" y="{y + 15}" font-size="12" fill="{T["muted"]}">{esc(cut(r["description"], 80))}</text>'
            f'<circle cx="712" cy="{y - 4}" r="5" fill="{lang["color"] or "#8b98b3"}"/>'
            f'<text x="724" y="{y}" font-size="12" fill="{T["text"]}">{esc(lang["name"])}</text>'
            f'<text x="836" y="{y}" font-size="12" text-anchor="end" fill="{T["a2"]}">★ {fmt(r["stargazerCount"])}</text>'
        )
        b.append(reveal(c, 0.4 + i * 0.2, dx=-14))
    return window(w, h, "projects.sh", "".join(b), u)


def main():
    cfg = load_cfg()
    ui.T.update(cfg.get("theme", {}))
    token = os.environ.get("GITHUB_TOKEN")
    if "--demo" in sys.argv or not token:
        raw = demo(cfg["login"])
    else:
        raw = fetch(cfg["login"], token)
    d = normalize(raw, cfg)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "stats.svg").write_text(stats_card(d), encoding="utf-8")
    (OUT / "langs.svg").write_text(langs_card(d), encoding="utf-8")
    (OUT / "contrib.svg").write_text(contrib_card(d), encoding="utf-8")
    (OUT / "projects.svg").write_text(projects_card(d), encoding="utf-8")


if __name__ == "__main__":
    main()
