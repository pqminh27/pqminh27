from pathlib import Path
import unittest
from unittest.mock import patch

import generate_snake


ROOT = Path(__file__).resolve().parents[2]


class ProfileSnakeReadmeTest(unittest.TestCase):
    def test_profile_uses_the_live_snake_in_both_themes(self):
        readme = (ROOT / "README.md").read_text()
        for theme in ("light", "dark"):
            self.assertIn(
                f"https://pqminh27-profile-snake.vercel.app/api/snake?theme={theme}",
                readme,
            )
        self.assertNotIn("profile-3d-contrib/profile-grid.svg", readme)

    def test_snake_uses_profile_calendar_counts_levels_and_dates(self):
        html = b"""
        <td class="ContributionCalendar-day" data-ix="0" data-date="2026-11-19"
            id="thursday" data-level="1"></td>
        <tool-tip for="thursday">1 contribution on November 19th.</tool-tip>
        <td class="ContributionCalendar-day" data-ix="0" data-date="2026-11-20"
            id="friday" data-level="4"></td>
        <tool-tip for="friday">9 contributions on November 20th.</tool-tip>
        <td class="ContributionCalendar-day" data-ix="0" data-date="2026-11-21"
            id="saturday" data-level="0"></td>
        <tool-tip for="saturday">No contributions on November 21st.</tool-tip>
        """
        with patch("generate_snake.urllib.request.urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = html
            weeks = generate_snake.fetch_weeks("pqminh27")

        self.assertEqual(
            urlopen.call_args.args[0].full_url,
            "https://github.com/users/pqminh27/contributions",
        )
        self.assertEqual(
            generate_snake.calendar_grid(weeks),
            ([[0, 0, 0, 0, 1, 4, 0]], [[0, 0, 0, 0, 1, 9, 0]]),
        )

class LiveSnakeTest(unittest.TestCase):
    def test_same_image_url_reflects_new_contributions(self):
        from threading import Thread
        from urllib.request import urlopen
        from serve_snake import SnakeHandler, ThreadingHTTPServer

        def calendar(count):
            return [{"contributionDays": [{
                "date": "2026-11-20",
                "contributionCount": count,
                "contributionLevel": 4,
            }]}]

        with (
            patch("serve_snake.fetch_weeks", side_effect=[calendar(9), calendar(10)]) as fetch,
            ThreadingHTTPServer(("127.0.0.1", 0), SnakeHandler) as server,
        ):
            thread = Thread(target=server.serve_forever)
            thread.start()
            try:
                url = f"http://127.0.0.1:{server.server_port}/api/snake?theme=dark"
                for count in (9, 10):
                    with urlopen(url, timeout=5) as response:
                        self.assertEqual(response.headers.get_content_type(), "image/svg+xml")
                        self.assertIn("no-store", response.headers["Cache-Control"])
                        self.assertIn(f">{count} contributions<", response.read().decode())
            finally:
                server.shutdown()
                thread.join()

        self.assertEqual(fetch.call_count, 2)


if __name__ == "__main__":
    unittest.main()
