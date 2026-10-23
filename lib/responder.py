from http.server import BaseHTTPRequestHandler
from xml.sax.saxutils import escape

CACHE_ERROR = "no-store"

SECURITY_HEADERS = (
    ("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; img-src data:; sandbox"),
    ("X-Content-Type-Options", "nosniff"),
    ("Referrer-Policy", "no-referrer"),
    ("Cross-Origin-Resource-Policy", "cross-origin"),
    ("Permissions-Policy", "camera=(), microphone=(), geolocation=()"),
)


def fallback_svg(title: str) -> str:
    safe = escape(title)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="120" viewBox="0 0 800 120" role="img">'
        '<defs><linearGradient id="e" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffffff" stop-opacity=".5"/>'
        '<stop offset="1" stop-color="#ffffff" stop-opacity=".1"/></linearGradient></defs>'
        '<rect width="800" height="120" rx="28" fill="#0a1030"/>'
        '<rect width="800" height="120" rx="28" fill="#ffffff" fill-opacity=".06"/>'
        '<rect x=".6" y=".6" width="798.8" height="118.8" rx="27.4" fill="none" stroke="url(#e)" stroke-width="1.2"/>'
        f'<text x="400" y="66" font-size="18" fill="#9aa7c7" text-anchor="middle" '
        f'font-family="-apple-system,BlinkMacSystemFont,\'SF Pro Text\',\'Segoe UI\',sans-serif">{safe} is temporarily unavailable</text>'
        "</svg>\n"
    )


def respond(handler: BaseHTTPRequestHandler, status: int, body: str, cache: str, head: bool = False) -> None:
    payload = body.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "image/svg+xml; charset=utf-8")
    handler.send_header("Cache-Control", cache)
    handler.send_header("Content-Length", str(len(payload)))
    for name, value in SECURITY_HEADERS:
        handler.send_header(name, value)
    handler.end_headers()
    if not head:
        handler.wfile.write(payload)
