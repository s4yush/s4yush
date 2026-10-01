import math
from pathlib import Path
import ui
from ui import T, esc, window, reveal, typed, cursor

OUT = Path(__file__).resolve().parent.parent / "assets"


def header():
    w, h, u = 900, 330, "h"
    b = []
    a, t, _ = typed(u, "a", 52, 92, [("s4yush@mac", T["a1"]), (" ~ % ", T["a3"]), ("whoami", T["text"])], 0.4)
    b.append(a)
    b.append(reveal(f'<text x="52" y="136" font-size="32" font-weight="800" fill="url(#tg{u})">Suyash Singh</text>', t + 0.2, dx=-14, dur=0.7))
    b.append(reveal(f'<text x="52" y="162" font-size="13" fill="{T["muted"]}">Product-minded developer  ·  B.Tech CSE</text>', t + 0.5))
    a, t2, ex = typed(u, "b", 52, 202, [("s4yush@mac", T["a1"]), (" ~ % ", T["a3"]), ("now --loop", T["text"])], t + 1.0)
    b.append(a)
    b.append(cursor(ex, 202, t2))
    roles = ["Python  ·  Automation", "Telegram bots  ·  Pyrogram", "FastAPI  ·  MongoDB  ·  Redis", "Learning & building in public"]
    for i, r in enumerate(roles):
        s = i / 4
        kt = [0, s, s + 0.02, s + 0.23, s + 0.25, 1]
        kt = [min(max(k, 0), 1) for k in kt]
        kts = ";".join(f"{k:.3f}" for k in kt)
        b.append(
            f'<text x="52" y="238" font-size="20" font-weight="700" fill="url(#tg{u})" opacity="0">'
            f'<animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="{kts}" dur="12s" begin="{t2 + 0.3:.2f}s" repeatCount="indefinite"/>{esc(r)}</text>'
        )
    b.append(
        '<circle cx="58" cy="270" r="4" fill="#28c840"><animate attributeName="r" values="4;6.5;4" dur="2s" repeatCount="indefinite"/>'
        '<animate attributeName="opacity" values="1;.35;1" dur="2s" repeatCount="indefinite"/></circle>'
        f'<text x="74" y="274" font-size="12" fill="{T["muted"]}">open to thoughtful teams  ·  ambitious products  ·  useful engineering work</text>'
    )
    return window(w, h, "suyash — zsh — 90×24", "".join(b), u)


def about():
    w, h, u = 820, 490, "a"
    kw, cls, base, attr, op, st, p = "#ff7b72", "#ffa657", "#79c0ff", "#7ee0ff", "#ff7b72", "#a5d6ff", "#c9d1d9"

    def lst(items):
        out = [("[", p)]
        for i, it in enumerate(items):
            if i:
                out.append((", ", p))
            out.append((f'"{it}"', st))
        out.append(("]", p))
        return out

    def attr_line(name, val):
        return (1, [(name.ljust(9), attr), ("= ", op)] + val)

    lines = [
        (0, [("class ", kw), ("Suyash", cls), ("(", p), ("Developer", base), ("):", p)]),
        attr_line("role", [('"Product-minded developer"', st)]),
        attr_line("education", [('"B.Tech CSE"', st)]),
        attr_line("stack", lst(["Python", "C", "Git", "GitHub"])),
        attr_line("focus", lst(["Telegram bots", "Automation", "Backend APIs"])),
        attr_line("status", [('"Learning & building in public"', st)]),
        attr_line("next_up", [('"More projects coming soon"', st)]),
        attr_line("open_to", [("[", p)]),
        (2, [('"Thoughtful teams"', st), (",", p)]),
        (2, [('"Ambitious products"', st), (",", p)]),
        (2, [('"Useful engineering work"', st), (",", p)]),
        (1, [("]", p)]),
    ]
    b = [f'<line x1="72" y1="62" x2="72" y2="{h - 50}" stroke="#1d2a47"/>']
    cw = 9.6
    last_x = 0
    for i, (ind, toks) in enumerate(lines):
        y = 102 + i * 30
        x = 88 + ind * 4 * cw
        spans = "".join(f'<tspan fill="{c}">{esc(t)}</tspan>' for t, c in toks)
        n = sum(len(t) for t, _ in toks)
        last_x = x + n * cw
        c = (
            f'<text x="60" y="{y}" font-size="13" text-anchor="end" fill="#34415f">{i + 1}</text>'
            f'<text x="{x}" y="{y}" font-size="16" xml:space="preserve">{spans}</text>'
        )
        b.append(reveal(c, 0.5 + i * 0.3))
    b.append(cursor(last_x, 102 + 11 * 30, 0.5 + 12 * 0.3))
    return window(w, h, "about.py", "".join(b), u)


def dock():
    w, h = 900, 215
    items = [
        ("Python", "Py", "#3776ab", "#ffd43b"),
        ("C", "C", "#5c6bc0", "#283593"),
        ("Git", "Git", "#f05133", "#b8321a"),
        ("GitHub", "GH", "#30363d", "#0d1117"),
        ("Pyrogram", "Pg", "#2aabee", "#1b6fb5"),
        ("FastAPI", "FA", "#05b09f", "#047a6f"),
        ("MongoDB", "Mo", "#13aa52", "#0b6b34"),
        ("Redis", "Rd", "#dc382d", "#9b1c14"),
        ("React", "Re", "#20232a", "#149eca"),
        ("Next.js", "Nx", "#000000", "#4a4a4a"),
        ("AWS", "AWS", "#ff9900", "#c26e00"),
        ("Telegram", "Tg", "#37aee2", "#1e96c8"),
    ]
    o = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        "<defs>",
        '<linearGradient id="glass" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".16"/><stop offset="1" stop-color="#fff" stop-opacity=".05"/></linearGradient>',
        f'<linearGradient id="dr" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{T["a1"]}" stop-opacity=".6"/><stop offset="1" stop-color="{T["a2"]}" stop-opacity=".6"/></linearGradient>',
        '<filter id="dsh" x="-10%" y="-30%" width="120%" height="200%"><feDropShadow dx="0" dy="16" stdDeviation="12" flood-color="#000" flood-opacity=".55"/></filter>',
    ]
    for i, (_, _, c1, c2) in enumerate(items):
        o.append(f'<linearGradient id="ic{i}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></linearGradient>')
    o += [
        "</defs>",
        f'<style>text{{font-family:{ui.MONO}}}</style>',
        '<rect x="30" y="92" width="840" height="100" rx="28" fill="#0b1324" filter="url(#dsh)"/>',
        '<rect x="30" y="92" width="840" height="100" rx="28" fill="url(#glass)" stroke="url(#dr)" stroke-width="1.2"/>',
        '<rect x="46" y="93" width="808" height="1.5" rx="1" fill="#fff" opacity=".25"/>',
    ]
    x0 = 48
    for i, (name, ab, c1, c2) in enumerate(items):
        x = x0 + i * 68
        fs = 14 if len(ab) > 2 else 19
        o.append(
            f'<g transform="translate({x} 106)"><g>'
            f'<animateTransform attributeName="transform" type="translate" values="0 0;0 -20;0 0;0 0" keyTimes="0;.06;.13;1" calcMode="spline" keySplines=".3 0 .3 1;.7 0 .7 1;0 0 1 1" dur="5s" begin="{i * 0.2:.1f}s" repeatCount="indefinite"/>'
            f'<rect width="56" height="56" rx="14" fill="url(#ic{i})" stroke="#fff" stroke-opacity=".28"/>'
            '<path d="M0 14A14 14 0 0 1 14 0H42A14 14 0 0 1 56 14V24Q28 36 0 24Z" fill="#fff" opacity=".17"/>'
            f'<text x="28" y="{35 if fs == 19 else 33}" text-anchor="middle" font-size="{fs}" font-weight="800" fill="#fff">{ab}</text>'
            "</g>"
            f'<text x="28" y="76" text-anchor="middle" font-size="10" fill="{T["muted"]}">{esc(name)}</text>'
            f'<circle cx="28" cy="86" r="2" fill="{T["a1"]}" opacity=".8"/></g>'
        )
    o.append("</svg>")
    return "".join(o)


def footer():
    w, h = 900, 150

    def wave(amp, off, y):
        pts = []
        for x in range(0, 1801, 15):
            pts.append(f"{x},{y + amp * math.sin((x + off) * 2 * math.pi / 450):.1f}")
        return "M" + " L".join(pts) + f" L1800,{h} L0,{h} Z"

    o = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        "<defs>",
        f'<linearGradient id="w1" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{T["a1"]}"/><stop offset="1" stop-color="{T["a2"]}"/></linearGradient>',
        "</defs>",
        f'<style>text{{font-family:{ui.MONO}}}</style>',
        f'<text x="450" y="44" text-anchor="middle" font-size="15" fill="{T["text"]}">thanks for stopping by</text>',
        f'<text x="450" y="68" text-anchor="middle" font-size="12" fill="{T["muted"]}">more projects coming soon</text>',
        f'<path d="{wave(10, 0, 100)}" fill="url(#w1)" opacity=".18"><animateTransform attributeName="transform" type="translate" from="0 0" to="-900 0" dur="11s" repeatCount="indefinite"/></path>',
        f'<path d="{wave(14, 150, 108)}" fill="url(#w1)" opacity=".3"><animateTransform attributeName="transform" type="translate" from="-900 0" to="0 0" dur="8s" repeatCount="indefinite"/></path>',
        f'<path d="{wave(8, 300, 120)}" fill="url(#w1)" opacity=".55"><animateTransform attributeName="transform" type="translate" from="0 0" to="-450 0" dur="5s" repeatCount="indefinite"/></path>',
        "</svg>",
    ]
    return "".join(o)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    (OUT / "header.svg").write_text(header(), encoding="utf-8")
    (OUT / "about.svg").write_text(about(), encoding="utf-8")
    (OUT / "stack.svg").write_text(dock(), encoding="utf-8")
    (OUT / "footer.svg").write_text(footer(), encoding="utf-8")
