import io
import sys
import tempfile
import unittest
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import refresh_stats


GOOD_SVG = b'''<svg xmlns="http://www.w3.org/2000/svg" width="120" height="40">
  <rect width="120" height="40" fill="#080A0F"/>
  <text x="4" y="24" fill="#F3F5F7">verified card</text>
</svg>'''
OLD_SVG = b'''<svg xmlns="http://www.w3.org/2000/svg" width="120" height="40">
  <rect width="120" height="40" fill="#0B1220"/>
  <text x="4" y="24" fill="#929BAA">previous snapshot</text>
</svg>'''
FALLBACK_SVG = b'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="180">
  <text x="10" y="30" fill="#F3F5F7">GitHub activity</text>
  <text x="10" y="60" fill="#FF2638">ACCOUNT NOT CONNECTED</text>
  <text x="10" y="90" fill="#929BAA">No statistics until a GitHub username is configured.</text>
</svg>'''


class FakeResponse(io.BytesIO):
    def __init__(self, payload, status=200, url="https://github-stats-extended.vercel.app/api"):
        super().__init__(payload)
        self.status = status
        self.url = url
        self.requested_limit = None

    def read(self, limit=-1):
        self.requested_limit = limit
        return super().read(limit)

    def geturl(self):
        return self.url

    def getcode(self):
        return self.status


class FakeOpener:
    def __init__(self, replies=None):
        self.replies = replies or {}
        self.requests = []
        self.responses = []

    def __call__(self, request, timeout):
        self.requests.append((request.full_url, timeout))
        path = urllib.parse.urlsplit(request.full_url).path
        reply = self.replies.get(path, GOOD_SVG)
        if isinstance(reply, FakeResponse):
            response = reply
        else:
            response = FakeResponse(reply, url=request.full_url)
        self.responses.append(response)
        return response


class RefreshStatsTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "assets/github").mkdir(parents=True)
        (self.root / "assets/github/unconfigured.svg").write_bytes(FALLBACK_SVG)

    def tearDown(self):
        self.tempdir.cleanup()

    def write_readme(self, body="old cards"):
        content = (
            "# Profile\n\nbefore\n"
            + refresh_stats.START_MARKER
            + "\n"
            + body
            + "\n"
            + refresh_stats.END_MARKER
            + "\n\nafter\n"
        )
        (self.root / "README.md").write_text(content, encoding="utf-8")

    def test_urls_use_documented_hosts_and_encoded_palette(self):
        urls = refresh_stats.build_urls("real-handle")
        self.assertEqual(set(urls), set(refresh_stats.SNAPSHOT_FILES))
        for url in urls.values():
            self.assertEqual(urllib.parse.urlsplit(url).scheme, "https")
            self.assertIn(urllib.parse.urlsplit(url).hostname, refresh_stats.ALLOWED_HOSTS)
            self.assertNotIn("#", url)
        stats_query = urllib.parse.parse_qs(urllib.parse.urlsplit(urls["stats"]).query)
        self.assertEqual(stats_query["username"], ["real-handle"])
        self.assertEqual(stats_query["theme"], ["dark"])
        self.assertEqual(stats_query["bg_color"], ["080A0F"])
        self.assertEqual(stats_query["title_color"], ["FF2638"])
        self.assertEqual(stats_query["icon_color"], ["45C7FF"])
        self.assertEqual(stats_query["hide_rank"], ["true"])
        languages_query = urllib.parse.urlsplit(urls["languages"]).query
        self.assertIn("custom_title=Most%20Used%20Languages", languages_query)
        activity_query = urllib.parse.parse_qs(urllib.parse.urlsplit(urls["activity"]).query)
        self.assertEqual(activity_query["theme"], ["github_dark"])
        self.assertEqual(activity_query["chart_color"], ["FF2638"])
        self.assertEqual(activity_query["animation"], ["none"])

    def test_validate_svg_accepts_static_svg_and_internal_fragments(self):
        refresh_stats.validate_svg(
            b'<svg xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="g"/></defs>'
            b'<rect style="fill:url(#g)"/></svg>'
        )

    def test_validate_svg_rejects_non_svg_and_unsafe_content(self):
        fixtures = [
            b"not an svg",
            b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
            b'<svg xmlns="http://www.w3.org/2000/svg"><foreignObject/></svg>',
            b'<svg xmlns="http://www.w3.org/2000/svg"><image href="https://evil.example/x"/></svg>',
            b'<svg xmlns="http://www.w3.org/2000/svg"><style>.x{background:url(font.woff)}</style></svg>',
            b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>',
            b'<svg xmlns="http://www.w3.org/2000/svg"><animate/></svg>',
            b'<svg xmlns="http://www.w3.org/2000/svg"><text>Something went wrong</text></svg>',
        ]
        for fixture in fixtures:
            with self.subTest(fixture=fixture):
                with self.assertRaises(refresh_stats.RefreshError):
                    refresh_stats.validate_svg(fixture)

    def test_fetch_has_timeout_size_bound_and_rejects_external_redirect(self):
        response = FakeResponse(GOOD_SVG)
        opener = FakeOpener({"/api": response})
        payload = refresh_stats.fetch_svg(
            "https://github-stats-extended.vercel.app/api?username=real-handle",
            opener=opener,
        )
        self.assertEqual(payload, GOOD_SVG)
        self.assertEqual(opener.requests[0][1], refresh_stats.TIMEOUT_SECONDS)
        self.assertEqual(response.requested_limit, refresh_stats.MAX_BYTES + 1)

        redirected = FakeOpener(
            {
                "/api": FakeResponse(
                    GOOD_SVG, url="https://evil.example/card.svg"
                )
            }
        )
        with self.assertRaises(refresh_stats.RefreshError):
            refresh_stats.fetch_svg(
                "https://github-stats-extended.vercel.app/api?username=real-handle",
                opener=redirected,
            )

    def test_placeholder_skips_network_and_uses_fallback_for_every_card(self):
        self.write_readme()

        def never_called(*args, **kwargs):
            raise AssertionError("placeholder must not make a request")

        errors = refresh_stats.refresh(
            refresh_stats.PLACEHOLDER, root=self.root, opener=never_called
        )
        self.assertEqual(errors, [])
        readme = (self.root / "README.md").read_text(encoding="utf-8")
        self.assertEqual(readme.count("assets/github/unconfigured.svg"), 4)
        self.assertIn("before", readme)
        self.assertIn("after", readme)

    def test_success_fetches_exactly_four_and_writes_local_cards(self):
        self.write_readme()
        opener = FakeOpener()
        errors = refresh_stats.refresh("real-handle", root=self.root, opener=opener)
        self.assertEqual(errors, [])
        self.assertEqual(len(opener.requests), refresh_stats.MAX_REQUESTS)
        for key, filename in refresh_stats.SNAPSHOT_FILES.items():
            self.assertEqual((self.root / "assets/github" / filename).read_bytes(), GOOD_SVG)
        readme = (self.root / "README.md").read_text(encoding="utf-8")
        for filename in refresh_stats.SNAPSHOT_FILES.values():
            self.assertIn(f"assets/github/{filename}", readme)
        self.assertNotIn("https://", readme)
        self.assertFalse(list((self.root / "assets/github").glob("*.tmp")))

    def test_service_error_keeps_previous_snapshot_and_reports_error(self):
        self.write_readme()
        stats_path = self.root / "assets/github/stats.svg"
        stats_path.write_bytes(OLD_SVG)
        opener = FakeOpener(
            {
                "/api": b'<svg xmlns="http://www.w3.org/2000/svg"><text>Error fetching data</text></svg>'
            }
        )
        errors = refresh_stats.refresh("real-handle", root=self.root, opener=opener)
        self.assertTrue(any(error.startswith("stats:") for error in errors))
        self.assertEqual(stats_path.read_bytes(), OLD_SVG)
        readme = (self.root / "README.md").read_text(encoding="utf-8")
        self.assertIn("assets/github/stats.svg", readme)
        self.assertIn("assets/github/languages.svg", readme)
        self.assertIn("assets/github/streak.svg", readme)
        self.assertIn("assets/github/activity.svg", readme)

    def test_invalid_old_snapshot_is_not_displayed(self):
        self.write_readme()
        invalid = self.root / "assets/github/stats.svg"
        invalid.write_bytes(b"<svg><script>bad</script></svg>")
        errors = refresh_stats.refresh(None, root=self.root)
        self.assertEqual(errors, [])
        readme = (self.root / "README.md").read_text(encoding="utf-8")
        self.assertNotIn('src="assets/github/stats.svg"', readme)
        self.assertIn('src="assets/github/unconfigured.svg"', readme)
        self.assertEqual(invalid.read_bytes(), b"<svg><script>bad</script></svg>")

    def test_missing_markers_are_reported_without_overwriting_readme(self):
        original = "# Profile\nno managed region\n"
        (self.root / "README.md").write_text(original, encoding="utf-8")
        errors = refresh_stats.refresh(None, root=self.root)
        self.assertTrue(any(error.startswith("README:") for error in errors))
        self.assertEqual((self.root / "README.md").read_text(encoding="utf-8"), original)

    def test_username_validation_and_explicit_absence(self):
        self.assertIsNone(refresh_stats.normalize_username(None))
        self.assertIsNone(refresh_stats.normalize_username(""))
        self.assertIsNone(refresh_stats.normalize_username(refresh_stats.PLACEHOLDER))
        self.assertEqual(refresh_stats.normalize_username("  real-handle  "), "real-handle")
        with self.assertRaises(refresh_stats.RefreshError):
            refresh_stats.normalize_username("not/a/handle")


if __name__ == "__main__":
    unittest.main()
