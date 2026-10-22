import sys
import traceback
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from cards import REGISTRY
from responder import CACHE_ERROR, fallback_svg, respond


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        name = parse_qs(urlparse(self.path).query).get("name", [""])[0].removesuffix(".svg")
        card = REGISTRY.get(name)
        if card is None:
            respond(self, 404, fallback_svg("Unknown card"), CACHE_ERROR)
            return
        try:
            svg = card.render()
        except Exception:
            traceback.print_exc(file=sys.stderr)
            svg = None
        if svg is None:
            respond(self, 502, fallback_svg(card.title), CACHE_ERROR)
            return
        respond(self, 200, svg, card.cache)

    def log_message(self, *args: object) -> None:
        return
