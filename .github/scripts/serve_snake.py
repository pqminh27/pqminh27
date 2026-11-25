"""Serve GitHub profile contribution snakes generated on demand."""

import os
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import URLError
from urllib.parse import parse_qs, urlsplit

from generate_snake import build_svg, fetch_weeks


LIGHT_THEME_COLORS = {
    "#161b22": "#ebedf0",
    "#0e4429": "#9be9a8",
    "#006d32": "#40c463",
    "#26a641": "#30a14e",
    "#39d353": "#216e39",
    "#b7ffd0": "#0d532a",
    "#8affc1": "#1a7f37",
    "#7d8590": "#57606a",
    "#0d1117": "#ffffff",
    "#30363d": "#d0d7de",
}


class SnakeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlsplit(self.path)
        theme = parse_qs(url.query).get("theme", ["light"])[0]
        if url.path != "/api/snake" or theme not in ("light", "dark"):
            self.send_error(404)
            return

        try:
            weeks = fetch_weeks("pqminh27")
            generated_at = datetime.now(timezone.utc).isoformat()
            svg = build_svg(weeks, generated_at)
        except (URLError, OSError, ValueError, KeyError) as error:
            print(f"Unable to generate contribution snake: {error}", file=sys.stderr)
            self.send_error(502, "GitHub contribution calendar unavailable")
            return

        if theme == "light":
            for dark, light in LIGHT_THEME_COLORS.items():
                svg = svg.replace(dark, light)

        content = svg.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "image/svg+xml; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, no-store, max-age=0, must-revalidate")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    with ThreadingHTTPServer(("0.0.0.0", port), SnakeHandler) as server:
        server.serve_forever()
