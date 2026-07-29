import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


def read(relative_path):
    return (FRONTEND / relative_path).read_text(encoding="utf-8")


class IntelligencePipelineFrontendTests(unittest.TestCase):
    def test_intelligence_pages_load_shared_auth_before_module_state(self):
        pages = {
            "coach.html": "coach-state.js",
            "knowledge.html": "knowledge-intelligence-state.js",
            "pattern-intelligence.html": "pattern-intelligence-state.js",
            "weekly-briefing.html": "weekly-briefing-state.js",
            "training-planner.html": "training-planner-state.js",
            "decision-engine.html": "decision-engine-state.js",
            "tactical-identity.html": "tactical-identity-state.js",
            "video.html": "video-intelligence.js",
            "index.html": "home-state.js",
        }
        for page, state_script in pages.items():
            with self.subTest(page=page):
                source = read(page)
                self.assertEqual(source.count("/js/auth.js"), 1)
                self.assertLess(source.index("/js/auth.js"), source.index(state_script))

    def test_intelligence_state_uses_canonical_auth_helper(self):
        state_scripts = (
            "js/knowledge-intelligence-state.js",
            "js/pattern-intelligence-state.js",
            "js/weekly-briefing-state.js",
            "js/training-planner-state.js",
            "js/tactical-identity-state.js",
            "js/decision-engine-state.js",
        )
        for script in state_scripts:
            with self.subTest(script=script):
                source = read(script)
                self.assertIn("MatchIQAuth", source)
                self.assertIn("matchiq_auth_token", source)
        self.assertNotIn(
            'localStorage.getItem("token")',
            read("js/knowledge-intelligence-state.js"),
        )

    def test_intelligence_api_requests_bypass_cache_and_share_credentials(self):
        api_scripts = (
            "js/knowledge-intelligence-api.js",
            "js/pattern-intelligence-api.js",
            "js/weekly-briefing-api.js",
            "js/training-planner-api.js",
            "js/tactical-identity-api.js",
            "js/decision-engine-api.js",
        )
        for script in api_scripts:
            with self.subTest(script=script):
                source = read(script)
                self.assertIn('cache:"no-store"', source)
                self.assertIn('credentials:"same-origin"', source)
                self.assertTrue(
                    "Authorization" in source
                    or ".headers()" in source
                    or ".authHeaders()" in source,
                    script,
                )

    def test_pwa_uses_current_intelligence_assets_and_never_caches_api(self):
        worker = read("service-worker.js")
        for asset in (
            "/js/weekly-briefing-state.js?v=10545",
            "/js/weekly-briefing-api.js?v=10545",
            "/js/pattern-intelligence-state.js?v=10545",
            "/js/pattern-intelligence-api.js?v=10545",
            "/js/training-planner-state.js?v=10546",
            "/js/training-planner-api.js?v=10546",
            "/js/knowledge-intelligence-state.js?v=10545",
            "/js/knowledge-intelligence-api.js?v=10545",
            "/js/tactical-identity-state.js?v=10545",
            "/js/tactical-identity-api.js?v=10545",
            "/js/decision-engine-state.js?v=10545",
            "/js/decision-engine-api.js?v=10545",
        ):
            self.assertIn(asset, worker)
        self.assertIn('url.pathname.startsWith("/api/")', worker)
        self.assertIn("fetch(request)", worker)
        self.assertIn("self.skipWaiting()", worker)
        self.assertIn("self.clients.claim()", worker)


if __name__ == "__main__":
    unittest.main()
