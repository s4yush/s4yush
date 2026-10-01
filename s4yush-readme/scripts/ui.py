from xml.sax.saxutils import escape

T = {
    "bg1": "#0f1b33",
    "bg2": "#070b14",
    "bar1": "#1c2740",
    "bar2": "#121a2c",
    "a1": "#5eead4",
    "a2": "#a78bfa",
    "a3": "#7aa2f7",
    "text": "#e6edf3",
    "muted": "#8b98b3",
    "grid": "#26334f",
}

MONO = "'JetBrains Mono','SF Mono','Fira Code',Menlo,Consolas,monospace"


def esc(s):
    return escape(str(s), {'"': "&quot;"})


def fmt(n):
    return f"{int(n):,}"


def defs(uid, w, h):
    cw = w - 40
    ch = h - 52
    return "".join([
        "<defs>",
        f'<linearGradient id="bg{uid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{T["bg1"]}"/><stop offset="1" stop-color="{T["bg2"]}"/></linearGradient>',
        f'<linearGradient id="bar{uid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{T["bar1"]}"/><stop offset="1" stop-color="{T["bar2"]}"/></linearGradient>',
        f'<linearGradient id="rim{uid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{T["a1"]}" stop-opacity=".75"/><stop offset=".5" stop-color="#3b4a6b" stop-opacity=".45"/><stop offset="1" stop-color="{T["a2"]}" stop-opacity=".75"/></linearGradient>',
        f'<linearGradient id="sheen{uid}" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".07"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>',
        f'<linearGradient id="tg{uid}" x1="0" y1="0" x2="1" y2="0" spreadMethod="reflect"><stop offset="0" stop-color="{T["a1"]}"/><stop offset=".5" stop-color="{T["a3"]}"/><stop offset="1" stop-color="{T["a2"]}"/><animate attributeName="x1" values="0;1" dur="5s" repeatCount="indefinite"/><animate attributeName="x2" values="1;2" dur="5s" repeatCount="indefinite"/></linearGradient>',
        f'<pattern id="dot{uid}" width="16" height="16" patternUnits="userSpaceOnUse"><circle cx="8" cy="8" r=".8" fill="{T["grid"]}"/></pattern>',
        f'<filter id="sh{uid}" x="-15%" y="-15%" width="130%" height="150%"><feDropShadow dx="0" dy="24" stdDeviation="16" flood-color="#000" flood-opacity=".6"/><feDropShadow dx="0" dy="0" stdDeviation="6" flood-color="{T["a1"]}" flood-opacity=".12"/></filter>',
        f'<clipPath id="cl{uid}"><rect x="20" y="14" width="{cw}" height="{ch}" rx="14"/></clipPath>',
        "</defs>",
    ])


def window(w, h, title, body, uid, float_=True):
    cw = w - 40
    ch = h - 52
    o = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        defs(uid, w, h),
        f'<style>text,tspan{{font-family:{MONO};white-space:pre}}</style>',
        "<g>",
    ]
    if float_:
        o.append('<animateTransform attributeName="transform" type="translate" values="0 0;0 -5;0 0" keyTimes="0;.5;1" calcMode="spline" keySplines=".45 0 .55 1;.45 0 .55 1" dur="6s" repeatCount="indefinite"/>')
    o += [
        f'<rect x="30" y="26" width="{cw - 20}" height="{ch}" rx="14" fill="#03060b"/>',
        f'<rect x="25" y="20" width="{cw - 10}" height="{ch}" rx="14" fill="#0a1020" stroke="#18233d"/>',
        f'<rect x="20" y="14" width="{cw}" height="{ch}" rx="14" fill="url(#bg{uid})" stroke="url(#rim{uid})" stroke-width="1.2" filter="url(#sh{uid})"/>',
        f'<g clip-path="url(#cl{uid})">',
        f'<rect x="20" y="50" width="{cw}" height="{ch - 36}" fill="url(#dot{uid})"/>',
        body,
        f'<rect x="20" y="14" width="{cw}" height="36" fill="url(#bar{uid})"/>',
        f'<line x1="20" y1="50" x2="{w - 20}" y2="50" stroke="#0a0f1c" stroke-width="1.5"/>',
        f'<line x1="20" y1="14.6" x2="{w - 20}" y2="14.6" stroke="#fff" stroke-opacity=".12"/>',
        '<circle cx="42" cy="32" r="6" fill="#ff5f57"/><circle cx="62" cy="32" r="6" fill="#febc2e"/><circle cx="82" cy="32" r="6" fill="#28c840"/>',
        '<circle cx="40.5" cy="30.2" r="2" fill="#fff" opacity=".35"/><circle cx="60.5" cy="30.2" r="2" fill="#fff" opacity=".35"/><circle cx="80.5" cy="30.2" r="2" fill="#fff" opacity=".35"/>',
        f'<text x="{w / 2}" y="37" text-anchor="middle" font-size="12" fill="{T["muted"]}">{esc(title)}</text>',
        f'<rect x="-200" y="14" width="160" height="{ch}" fill="url(#sheen{uid})"><animate attributeName="x" values="-200;{w + 60}" dur="7s" begin="1s" repeatCount="indefinite"/></rect>',
        "</g>",
        "</g></svg>",
    ]
    return "".join(o)


def reveal(content, begin, dx=-10, dur=0.5):
    return (
        f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" dur="{dur}s" begin="{begin:.2f}s" fill="freeze"/>'
        f'<animateTransform attributeName="transform" type="translate" from="{dx} 0" to="0 0" dur="{dur}s" begin="{begin:.2f}s" fill="freeze"/>'
        f"{content}</g>"
    )


def typed(uid, key, x, y, tokens, begin, step=0.055, size=16, cw=9.6):
    n = sum(len(t) for t, _ in tokens)
    vals = ";".join(f"{i * cw:.1f}" for i in range(n + 1))
    dur = n * step
    cid = f"ty{uid}{key}"
    spans = "".join(f'<tspan fill="{c}">{esc(t)}</tspan>' for t, c in tokens)
    s = (
        f'<clipPath id="{cid}"><rect x="{x}" y="{y - size - 2}" width="0" height="{size + 10}">'
        f'<animate attributeName="width" values="{vals}" dur="{dur:.2f}s" begin="{begin:.2f}s" calcMode="discrete" fill="freeze"/></rect></clipPath>'
        f'<text x="{x}" y="{y}" font-size="{size}" xml:space="preserve" clip-path="url(#{cid})">{spans}</text>'
    )
    return s, begin + dur, x + n * cw


def cursor(x, y, begin, size=16, color=None):
    c = color or T["a1"]
    return (
        f'<rect x="{x + 2:.1f}" y="{y - size + 2}" width="{size * 0.55:.1f}" height="{size}" fill="{c}" opacity="0">'
        f'<animate attributeName="opacity" values="0;1" calcMode="discrete" dur="1s" begin="{begin:.2f}s" repeatCount="indefinite"/></rect>'
    )
