const MIN_DIGITS = 6;
const DIGIT_AREA = 234;
const DIGIT_GAP = 6;
const HEADERS = {
  "Content-Type": "image/svg+xml; charset=utf-8",
  "Cache-Control": "no-cache, no-store, max-age=0, must-revalidate",
  "Access-Control-Allow-Origin": "*",
};

const STYLE = [
  "text{font-family:'Segoe UI',-apple-system,BlinkMacSystemFont,Roboto,'Helvetica Neue',Arial,sans-serif}",
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
].join("");

const escapeXml = (value) =>
  String(value).replace(/[&<>"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[char]);

function shuriken(x, y, scale, color) {
  return `<g transform="translate(${x} ${y}) scale(${scale})"><g class="spin"><path d="M0,-12 L3,-3 L12,0 L3,3 L0,12 L-3,3 L-12,0 L-3,-3 Z" fill="${color}"/><circle r="2.4" fill="#0d1117"/></g></g>`;
}

function ninja() {
  return `
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
</g>`;
}

function digits(count) {
  const text = String(count).padStart(MIN_DIGITS, "0");
  const real = String(count).length;
  const width = Math.min(34, (DIGIT_AREA - DIGIT_GAP * (text.length - 1)) / text.length);
  const startX = 160;
  return [...text]
    .map((char, index) => {
      const x = startX + index * (width + DIGIT_GAP);
      const lit = index >= text.length - real;
      return `<g class="pop" style="animation-delay:${(index * 0.06).toFixed(2)}s">
  <rect x="${x.toFixed(1)}" y="50" width="${width.toFixed(1)}" height="48" rx="9" fill="#161b22" stroke="${lit ? "#3b82f6" : "#30363d"}" stroke-opacity="${lit ? ".7" : "1"}"/>
  <rect x="${(x + 1).toFixed(1)}" y="73" width="${(width - 2).toFixed(1)}" height="2" fill="#0d1117"/>
  <text class="mono" x="${(x + width / 2).toFixed(1)}" y="84" font-size="${(width * 0.92).toFixed(1)}" font-weight="800" text-anchor="middle" fill="${lit ? "#e6edf3" : "#3d444d"}">${char}</text>
</g>`;
    })
    .join("");
}

function renderCounter(count, id) {
  const label = `Profile views: ${count.toLocaleString("en-US")}`;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="420" height="150" viewBox="0 0 420 150" role="img" aria-label="${escapeXml(label)}">
<title>${escapeXml(label)}</title>
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#0d1117"/><stop offset="100%" stop-color="#131b2e"/></linearGradient>
  <linearGradient id="hood" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#2d3d7a"/><stop offset="100%" stop-color="#1e2a52"/></linearGradient>
  <radialGradient id="aura" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#8b5cf6" stop-opacity=".45"/><stop offset="100%" stop-color="#8b5cf6" stop-opacity="0"/></radialGradient>
  <pattern id="dots" width="18" height="18" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="#fff" fill-opacity=".05"/></pattern>
</defs>
<style>${STYLE}</style>
<rect width="420" height="150" rx="20" fill="url(#bg)"/>
<rect width="420" height="150" rx="20" fill="url(#dots)"/>
<rect x=".5" y=".5" width="419" height="149" rx="19.5" fill="none" stroke="#30363d"/>
<circle class="glow" cx="80" cy="76" r="62" fill="url(#aura)"/>
${ninja()}
${shuriken(396, 26, 0.9, "#94a3b8")}
<text x="160" y="34" font-size="12" font-weight="700" letter-spacing="3" fill="#8b949e">PROFILE VIEWS</text>
${digits(count)}
<text x="160" y="126" font-size="12.5" font-weight="500" fill="#8b949e">Kage the shadow runner  \u00b7  @${escapeXml(id)}</text>
</svg>
`;
}

const IST_OFFSET_MS = (5 * 60 + 30) * 60 * 1000;
const WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const HOUR_TENS = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1];
const HOUR_ONES = [2, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0, 1];
const SECONDS_IN_DAY = 86400;

function istParts(date) {
  const shifted = new Date(date.getTime() + IST_OFFSET_MS);
  return {
    hour24: shifted.getUTCHours(),
    minute: shifted.getUTCMinutes(),
    second: shifted.getUTCSeconds() + shifted.getUTCMilliseconds() / 1000,
    day: shifted.getUTCDay(),
  };
}

function renderClock(id, date = new Date()) {
  const { hour24, minute, second, day } = istParts(date);
  const secondsOfDay = hour24 * 3600 + minute * 60 + second;
  const digitW = 40;
  const digitH = 56;
  const gap = 6;
  const colonW = 16;
  const top = 30;
  const keyframes = new Set();
  const clips = [];

  const column = (values, startIndex, period, elapsed, x, y, w, h, anchorX, anchor, size, fill, weight, mono) => {
    const clipId = `c${clips.length}`;
    clips.push(`<clipPath id="${clipId}"><rect x="${x.toFixed(1)}" y="${y}" width="${w}" height="${h}"/></clipPath>`);
    const name = `r${values.length}x${h}`;
    keyframes.add(`@keyframes ${name}{from{transform:translateY(0)}to{transform:translateY(-${values.length * h}px)}}`);
    const baseline = y + h * 0.7;
    const items = values
      .map(
        (value, index) =>
          `<text${mono ? ' class="mono"' : ""} x="${anchorX.toFixed(1)}" y="${(baseline + index * h).toFixed(1)}" font-size="${size}" font-weight="${weight}" text-anchor="${anchor}" fill="${fill}">${escapeXml(value)}</text>`,
      )
      .join("");
    const motion = `animation-name:${name};animation-duration:${period}s;animation-timing-function:steps(${values.length},end);animation-iteration-count:infinite;animation-delay:-${elapsed.toFixed(3)}s`;
    return `<g clip-path="url(#${clipId})"><g style="transform:translateY(-${startIndex * h}px);${motion}">${items}</g></g>`;
  };

  const slots = [
    { type: "digit", values: HOUR_TENS, start: hour24 % 12, period: 43200, elapsed: (hour24 % 12) * 3600 + minute * 60 + second },
    { type: "digit", values: HOUR_ONES, start: hour24 % 12, period: 43200, elapsed: (hour24 % 12) * 3600 + minute * 60 + second },
    { type: "colon" },
    { type: "digit", values: [0, 1, 2, 3, 4, 5], start: Math.floor(minute / 10), period: 3600, elapsed: minute * 60 + second },
    { type: "digit", values: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], start: minute % 10, period: 600, elapsed: (minute % 10) * 60 + second },
    { type: "colon" },
    { type: "digit", values: [0, 1, 2, 3, 4, 5], start: Math.floor(second / 10), period: 60, elapsed: second },
    { type: "digit", values: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], start: Math.floor(second % 10), period: 10, elapsed: second % 10 },
  ];
  const totalW = slots.reduce((sum, slot) => sum + (slot.type === "colon" ? colonW : digitW) + gap, 0) - gap;
  let x = (440 - totalW) / 2;
  const glyphs = slots
    .map((slot) => {
      if (slot.type === "colon") {
        const cx = (x + colonW / 2).toFixed(1);
        const mid = top + digitH / 2;
        x += colonW + gap;
        return `<circle cx="${cx}" cy="${mid - 12}" r="3" fill="#8b949e"/><circle cx="${cx}" cy="${mid + 12}" r="3" fill="#8b949e"/>`;
      }
      const box = `<rect x="${x.toFixed(1)}" y="${top}" width="${digitW}" height="${digitH}" rx="9" fill="#161b22" stroke="#3b82f6"/>`;
      const roll = column(slot.values, slot.start, slot.period, slot.elapsed, x, top, digitW, digitH, x + digitW / 2, "middle", (digitH * 0.62).toFixed(1), "#e6edf3", 800, true);
      x += digitW + gap;
      return `<g>${box}${roll}</g>`;
    })
    .join("");

  const isPm = hour24 >= 12;
  const ampmMotion = (name) =>
    `animation-name:${name};animation-duration:${SECONDS_IN_DAY}s;animation-timing-function:linear;animation-iteration-count:infinite;animation-delay:-${secondsOfDay.toFixed(3)}s`;
  keyframes.add("@keyframes am{0%,49.9999%{opacity:1}50%,100%{opacity:0}}");
  keyframes.add("@keyframes pm{0%,49.9999%{opacity:0}50%,100%{opacity:1}}");
  const period = `<text x="220" y="112" font-size="14" font-weight="700" fill="#58a6ff" text-anchor="middle" style="opacity:${isPm ? 0 : 1};${ampmMotion("am")}">AM</text><text x="220" y="112" font-size="14" font-weight="700" fill="#58a6ff" text-anchor="middle" style="opacity:${isPm ? 1 : 0};${ampmMotion("pm")}">PM</text>`;

  const weekday = column(
    WEEKDAYS,
    day,
    604800,
    day * SECONDS_IN_DAY + secondsOfDay,
    70,
    120,
    300,
    22,
    220,
    "middle",
    13,
    "#8b949e",
    500,
    false,
  );

  const hh = String(hour24 % 12 === 0 ? 12 : hour24 % 12).padStart(2, "0");
  const label = `IST time: ${hh}:${String(minute).padStart(2, "0")}:${String(Math.floor(second)).padStart(2, "0")} ${isPm ? "PM" : "AM"}, ${WEEKDAYS[day]}`;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="440" height="150" viewBox="0 0 440 150" role="img" aria-label="${escapeXml(label)}">
<title>${escapeXml(label)}</title>
<defs>
  <linearGradient id="clock-bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#0d1117"/><stop offset="100%" stop-color="#131b2e"/></linearGradient>
  ${clips.join("")}
</defs>
<style>${STYLE}${[...keyframes].join("")}</style>
<rect width="440" height="150" rx="20" fill="url(#clock-bg)"/>
<rect x=".5" y=".5" width="439" height="149" rx="19.5" fill="none" stroke="#30363d"/>
<text x="220" y="24" font-size="12" font-weight="700" letter-spacing="3" fill="#8b949e" text-anchor="middle">LIVE IN INDIA \u00b7 IST</text>
${glyphs}
${period}
${weekday}
</svg>
`;
}

const clean = (value) => value.toLowerCase().replace(/[^a-z0-9-_]/g, "").slice(0, 39);

export default {
  async fetch(request, env) {
    const [route, rawId] = new URL(request.url).pathname.split("/").filter(Boolean);
    const id = clean(rawId ?? "");
    const allowed = (env.ALLOWED_IDS ?? "").split(",").map((entry) => clean(entry.trim())).filter(Boolean);
    if (!id || (allowed.length && !allowed.includes(id))) {
      return new Response("Not found", { status: 404 });
    }

    if (route === "clock") {
      if (request.method === "HEAD") return new Response(null, { headers: HEADERS });
      return new Response(renderClock(id), { headers: HEADERS });
    }

    if (route !== "views") {
      return new Response("Not found", { status: 404 });
    }
    const key = `views:${id}`;
    let count = parseInt((await env.VIEWS.get(key)) ?? "0", 10) || 0;
    if (request.method === "GET") {
      count += 1;
      try {
        await env.VIEWS.put(key, String(count));
      } catch {
        count -= 1;
      }
    }
    return new Response(request.method === "HEAD" ? null : renderCounter(count, id), { headers: HEADERS });
  },
};
