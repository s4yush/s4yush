from http.server import BaseHTTPRequestHandler

CACHE_ERROR = "no-store"


def fallback_svg(title: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="120" viewBox="0 0 800 120" role="img">'
        '<rect width="800" height="120" rx="20" fill="#0d1117" stroke="#30363d"/>'
        f'<text x="400" y="66" font-size="18" fill="#8b949e" text-anchor="middle" font-family="sans-serif">{title} is temporarily unavailable</text>'
        "</svg>\n"
    )


def respond(handler: BaseHTTPRequestHandler, status: int, body: str, cache: str) -> None:
    payload = body.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "image/svg+xml; charset=utf-8")
    handler.send_header("Cache-Control", cache)
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)
