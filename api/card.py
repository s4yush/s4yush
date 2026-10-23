import re
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from cards import REGISTRY, render_card
from responder import CACHE_ERROR, fallback_svg, respond

NAME_PATTERN = re.compile(r"[a-z]{1,24}")


class handler(BaseHTTPRequestHandler):
    def serve(self, head: bool) -> None:
        raw = parse_qs(urlparse(self.path).query).get("name", [""])[0].removesuffix(".svg")
        card = REGISTRY.get(raw) if NAME_PATTERN.fullmatch(raw) else None
        if card is None:
            respond(self, 404, fallback_svg("Unknown card"), CACHE_ERROR, head)
            return
        svg, cache = render_card(raw, card)
        if svg is None:
            respond(self, 502, fallback_svg(card.title), CACHE_ERROR, head)
            return
        respond(self, 200, svg, cache, head)

    def do_GET(self) -> None:
        self.serve(False)

    def do_HEAD(self) -> None:
        self.serve(True)

    def log_message(self, *args: object) -> None:
        return
