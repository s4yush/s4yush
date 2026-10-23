from __future__ import annotations

import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

import build_assets as ba

IST = timezone(timedelta(hours=5, minutes=30))
COUNTER_URL = "https://komarev.com/ghpvc/?username={login}"
MIN_DIGITS = 6
DIGIT_AREA = 234
DIGIT_GAP = 6

STYLE = "".join(
    (
        "text{font-family:-apple-system,BlinkMacSystemFont,'SF Pro Display','SF Pro Text','Inter','Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif}",
        ".mono{font-family:'SFMono-Regular',Consolas,'Liberation Mono',Menlo,'DejaVu Sans Mono',monospace}",
        ".bob{animation:bob 2.4s ease-in-out infinite}",
        ".scarf{transform-box:fill-box;transform-origin:0% 50%;animation:wave 1.4s ease-in-out infinite alternate}",
        ".tail{transform-box:fill-box;transform-origin:0% 50%;animation:wave 1.1s ease-in-out infinite alternate-reverse}",
        ".spin{transform-box:fill-box;transform-origin:center;animation:spin 3.2s linear infinite}",
        ".blink{transform-box:fill-box;transform-origin:center;animation:blink 4.2s infinite}",
        ".pop{animation:pop .6s cubic-bezier(.2,.7,.2,1) both}",
        ".glow{animation:glow 2.2s ease-in-out infinite}",
        "@keyframes bob{0%,100%{transform:translateY(0)}50%{transform:translateY(-4px)}}",
        "@keyframes wave{from{transform:rotate(-6deg)}to{transform:rotate(9deg)}}",
        "@keyframes spin{to{transform:rotate(360deg)}}",
        "@keyframes blink{0%,92%,100%{transform:scaleY(1)}96%{transform:scaleY(.1)}}",
        "@keyframes pop{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}",
        "@keyframes glow{0%,100%{opacity:.55}50%{opacity:1}}",
        "@media (prefers-reduced-motion:reduce){*{animation:none!important}}",
    )
)

NINJA = """
<ellipse cx="78" cy="134" rx="30" ry="5" fill="#000" opacity=".35"/>
<g class="bob">
  <path class="scarf" d="M98,86 Q118,74 134,88 Q118,95 100,94 Z" fill="#14b8a6"/>
  <path class="tail" d="M98,92 Q116,100 130,114 Q112,110 98,100 Z" fill="#5eead4"/>
  <rect x="62" y="120" width="11" height="14" rx="4" fill="#141b36"/>
  <rect x="83" y="120" width="11" height="14" rx="4" fill="#141b36"/>
  <rect x="56" y="92" width="44" height="34" rx="13" fill="#1e2a52"/>
  <rect x="56" y="108" width="44" height="6" fill="#14b8a6"/>
  <polygon points="78,106 82,111 78,116 74,111" fill="#cbd5e1"/>
  <ellipse cx="53" cy="106" rx="6" ry="10" fill="#1e2a52"/>
  <ellipse cx="103" cy="106" rx="6" ry="10" fill="#1e2a52"/>
  <circle cx="78" cy="64" r="32" fill="url(#hood)"/>
  <ellipse cx="78" cy="68" rx="22" ry="15" fill="#f1c7a0"/>
  <path d="M56,70 Q78,80 100,70 Q98,92 78,94 Q58,92 56,70 Z" fill="#14b8a6"/>
  <g class="blink">
    <ellipse cx="68" cy="66" rx="4.6" ry="5.4" fill="#fff"/>
    <ellipse cx="88" cy="66" rx="4.6" ry="5.4" fill="#fff"/>
    <circle cx="68.6" cy="66.4" r="2.9" fill="#8b5cf6"/>
    <circle cx="88.6" cy="66.4" r="2.9" fill="#8b5cf6"/>
    <circle cx="68.6" cy="66.4" r="1.2" fill="#0d1117"/>
    <circle cx="88.6" cy="66.4" r="1.2" fill="#0d1117"/>
    <circle cx="67.6" cy="65" r=".9" fill="#fff"/>
    <circle cx="87.6" cy="65" r=".9" fill="#fff"/>
  </g>
  <path d="M62,58 L73,60 M94,58 L83,60" stroke="#26346a" stroke-width="2.2" stroke-linecap="round"/>
  <path class="tail" d="M108,54 Q124,50 138,62 L134,67 Q122,60 108,61 Z" fill="#3b82f6"/>
  <path d="M47,52 Q78,41 109,52 L108,61 Q78,50 48,61 Z" fill="#3b82f6"/>
  <rect x="66" y="43" width="24" height="15" rx="3.5" fill="#cbd5e1" stroke="#94a3b8"/>
  <polygon points="78,46.5 83,50.5 78,54.5 73,50.5" fill="#334155"/>
</g>"""


def shuriken(x: float, y: float, scale: float, color: str) -> str:
    return (
        f'<g transform="translate({x} {y}) scale({scale})"><g class="spin">'
        f'<path d="M0,-12 L3,-3 L12,0 L3,3 L0,12 L-3,3 L-12,0 L-3,-3 Z" fill="{color}"/>'
        '<circle r="2.4" fill="#0d1117"/></g></g>'
    )


def digits(count: int) -> str:
    text = str(count).zfill(MIN_DIGITS)
    real = len(str(count))
    width = min(34.0, (DIGIT_AREA - DIGIT_GAP * (len(text) - 1)) / len(text))
    parts = []
    for index, char in enumerate(text):
        x = 160 + index * (width + DIGIT_GAP)
        lit = index >= len(text) - real
        parts.append(
            f'<g class="pop" style="animation-delay:{index * 0.06:.2f}s">'
            f'<rect x="{x:.1f}" y="50" width="{width:.1f}" height="48" rx="9" fill="url(#g-tile)" '
            f'stroke="{"#0a84ff" if lit else "#34406a"}" stroke-opacity="{".7" if lit else "1"}"/>'
            f'<rect x="{x + 1:.1f}" y="73" width="{width - 2:.1f}" height="2" fill="#000" fill-opacity=".22"/>'
            f'<text class="mono" x="{x + width / 2:.1f}" y="84" font-size="{width * 0.92:.1f}" '
            f'font-weight="800" text-anchor="middle" fill="{"#f5f7ff" if lit else "#4a5578"}">{char}</text>'
            "</g>"
        )
    return "".join(parts)


def render_views(count: int, login: str) -> str:
    label = f"Profile views: {count:,}"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="420" height="150" viewBox="0 0 420 150" role="img" aria-label="{ba.esc(label)}">
<title>{ba.esc(label)}</title>
<defs>
  {ba.glass_markup()}
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#040716"/><stop offset="100%" stop-color="#0c0b3c"/></linearGradient>
  <linearGradient id="hood" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#2d3d7a"/><stop offset="100%" stop-color="#1e2a52"/></linearGradient>
  <radialGradient id="aura" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#8b5cf6" stop-opacity=".45"/><stop offset="100%" stop-color="#8b5cf6" stop-opacity="0"/></radialGradient>
  <pattern id="dots" width="18" height="18" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="#fff" fill-opacity=".05"/></pattern>
</defs>
<style>{STYLE}</style>
<rect width="420" height="150" rx="28" fill="url(#bg)"/>
<rect width="420" height="150" rx="28" fill="url(#g-panel)"/>
<rect width="420" height="52" rx="28" fill="url(#g-shine)"/>
<rect x=".6" y=".6" width="418.8" height="148.8" rx="27.4" fill="none" stroke="url(#g-edge)" stroke-width="1.2"/>
<circle class="glow" cx="80" cy="76" r="62" fill="url(#aura)"/>
{NINJA}
{shuriken(396, 26, 0.9, "#94a3b8")}
<text x="160" y="34" font-size="12" font-weight="700" letter-spacing="3" fill="#9aa7c7">PROFILE VIEWS</text>
{digits(count)}
<text x="160" y="126" font-size="12.5" font-weight="500" fill="#9aa7c7">Kage the shadow runner  \u00b7  @{ba.esc(login)}</text>
</svg>
"""


def render_clock(now_utc: datetime) -> str:
    now = now_utc.astimezone(IST)
    hh = f"{now.hour % 12 or 12:02d}"
    mm = f"{now.minute:02d}"
    period = "AM" if now.hour < 12 else "PM"
    weekday = now.strftime("%A")
    digit_w, digit_h, gap, colon_w = 46, 60, 6, 18
    chars = [*hh, ":", *mm]
    total = sum((colon_w if char == ":" else digit_w) + gap for char in chars) - gap
    x = (440 - total) / 2
    glyphs = []
    for char in chars:
        if char == ":":
            cx = x + colon_w / 2
            mid = 36 + digit_h / 2
            glyphs.append(
                f'<circle cx="{cx:.1f}" cy="{mid - 12:.1f}" r="3" fill="#9aa7c7"/>'
                f'<circle cx="{cx:.1f}" cy="{mid + 12:.1f}" r="3" fill="#9aa7c7"/>'
            )
            x += colon_w + gap
            continue
        glyphs.append(
            f'<g><rect x="{x:.1f}" y="36" width="{digit_w}" height="{digit_h}" rx="9" fill="url(#g-tile)" stroke="url(#g-edge)"/>'
            f'<text class="mono" x="{x + digit_w / 2:.1f}" y="{36 + digit_h * 0.7:.1f}" font-size="{digit_h * 0.62:.1f}" '
            f'font-weight="800" text-anchor="middle" fill="#f5f7ff">{char}</text></g>'
        )
        x += digit_w + gap
    label = f"India time: {hh}:{mm} {period}, {weekday}"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="440" height="150" viewBox="0 0 440 150" role="img" aria-label="{ba.esc(label)}">
<title>{ba.esc(label)}</title>
<defs>
  {ba.glass_markup()}
  <linearGradient id="clock-bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#040716"/><stop offset="100%" stop-color="#0c0b3c"/></linearGradient>
</defs>
<style>{STYLE}</style>
<rect width="440" height="150" rx="28" fill="url(#clock-bg)"/>
<rect width="440" height="150" rx="28" fill="url(#g-panel)"/>
<rect width="440" height="52" rx="28" fill="url(#g-shine)"/>
<rect x=".6" y=".6" width="438.8" height="148.8" rx="27.4" fill="none" stroke="url(#g-edge)" stroke-width="1.2"/>
<text x="220" y="22" font-size="12" font-weight="700" letter-spacing="3" fill="#9aa7c7" text-anchor="middle">INDIA TIME \u00b7 IST</text>
{"".join(glyphs)}
<text x="220" y="112" font-size="14" font-weight="700" fill="#64d2ff" text-anchor="middle">{period}</text>
<text x="220" y="134" font-size="13" font-weight="500" fill="#9aa7c7" text-anchor="middle">{weekday} \u00b7 live</text>
</svg>
"""


NUMBER = r"(\d[\d,]*(?:\.\d+)?)\s*([KkMm]?)"


def to_int(digits_text: str, suffix: str) -> int:
    scale = {"": 1, "k": 1_000, "m": 1_000_000}[suffix.lower()]
    return int(round(float(digits_text.replace(",", "")) * scale))


def parse_count(svg: str) -> int | None:
    for pattern in (r'aria-label="[^"]*:\s*' + NUMBER + '"', r"<title>[^<]*:\s*" + NUMBER + "</title>"):
        match = re.search(pattern, svg)
        if match:
            return to_int(match.group(1), match.group(2))
    texts = re.findall(r">\s*(\d[\d,]*)\s*</text>", svg)
    return to_int(texts[-1], "") if texts else None


def fetch_count(login: str) -> int:
    request = urllib.request.Request(COUNTER_URL.format(login=urllib.parse.quote(login, safe="")), headers={"User-Agent": "profile-assets-builder"})
    with urllib.request.urlopen(request, timeout=20) as response:
        body = response.read(1_000_000).decode("utf-8", "replace")
    count = parse_count(body)
    if count is None:
        raise ValueError(f"no number found in the counter response, which starts with: {body[:200]!r}")
    return count
