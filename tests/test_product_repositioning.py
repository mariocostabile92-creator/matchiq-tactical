import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


def read_frontend(relative_path):
    return (FRONTEND / relative_path).read_text(encoding="utf-8")


def body_of(relative_path):
    source = read_frontend(relative_path)
    return source.split("<body", 1)[1] if "<body" in source else source


class ProductRepositioningTests(unittest.TestCase):
    def test_coach_ai_identity_and_positioning_are_consistent(self):
        home = read_frontend("index.html")
        landing = read_frontend("lp.html")
        app_meta = read_frontend("js/app-meta.js")

        self.assertIn("MatchIQ Coach AI", home)
        self.assertIn("MatchIQ Coach AI", landing)
        self.assertIn('product: "MatchIQ Coach AI"', app_meta)
        self.assertIn("La scrivania digitale dell'allenatore.", home)
        self.assertIn(
            "L'assistente AI che accompagna lo staff tecnico prima, durante e dopo ogni partita.",
            landing,
        )

    def test_primary_navigation_contains_only_coach_ai_workspace(self):
        config = read_frontend("js/global-nav-config.js")
        navigation = config.split("const navigation = [", 1)[1].split("];", 1)[0]

        self.assertEqual(re.findall(r'key: "([^"]+)"', navigation), ["home", "coach", "video", "account"])
        self.assertIn('key: "home", label: "Oggi"', navigation)
        self.assertNotIn('key: "live"', navigation)
        self.assertNotIn('key: "scout"', navigation)
        self.assertIn('live: { title: "MatchIQ Live"', config)
        self.assertIn('scout: { title: "MatchIQ Scout"', config)

    def test_home_exposes_staff_workflow_without_live_or_scout(self):
        home = body_of("index.html")

        for section_id in (
            "todayHero", "todayPriorities", "todayContinue", "nextMatch",
            "weeklyBriefing", "videoFocus", "weeklyFlow",
            "homeIntelligence", "recentWork",
        ):
            self.assertIn(f'id="{section_id}"', home)
        self.assertNotIn('href="/video.html#hubArchivePane"', home)
        self.assertNotIn('href="/live.html"', home)
        self.assertNotIn('href="/scout.html"', home)

    def test_auth_and_landing_present_coach_ai_only(self):
        for page in ("login.html", "register.html"):
            body = body_of(page)
            self.assertIn("MatchIQ Coach AI", body)
            self.assertIn("PREPARA", body)
            self.assertIn("VIVI IL MATCH", body)
            self.assertIn("ANALIZZA", body)
            self.assertNotIn('href="/live.html', body)
            self.assertNotIn('href="/scout.html', body)

        landing = body_of("lp.html")
        self.assertIn("MatchIQ Coach AI Private Beta", landing)
        self.assertNotIn('href="/live.html', landing)
        self.assertNotIn('href="/scout.html', landing)
        self.assertNotIn("MatchIQ Pro", landing)

    def test_private_beta_hides_public_commercial_panels(self):
        account = read_frontend("account.html")
        video = read_frontend("video.html")

        self.assertIn("Account Private Beta - MatchIQ Coach AI", account)
        for panel in ("#ctaPanel", "#proOnlyPanel", "#valuePanel", "#founderPanel", "#comparePanel"):
            self.assertIn(panel, account)
        self.assertIn("display:none !important", account)
        self.assertIn("Durante la Private Beta l'accesso commerciale non viene mostrato pubblicamente.", account)
        self.assertIn('<div class="plan-kicker">Private Beta</div>', video)

    def test_match_day_labels_use_coach_ai_terminology(self):
        coach = read_frontend("coach.html")

        self.assertIn("MATCH DAY ASSISTANT", coach)
        self.assertIn("AI MATCH DAY ASSISTANT", coach)
        self.assertIn("Ultimo evento del match", coach)
        self.assertNotIn("COACH LIVE ASSISTANT", coach)
        self.assertNotIn("AI ASSISTANT LIVE", coach)
        self.assertNotIn("Ultimo evento live", coach)

    def test_pwa_release_uses_one_coach_ai_identity(self):
        manifest = json.loads(read_frontend("manifest.json"))
        worker = read_frontend("service-worker.js")
        app_meta = read_frontend("js/app-meta.js")
        config = read_frontend("js/global-nav-config.js")

        self.assertEqual(manifest["name"], "MatchIQ Coach AI")
        self.assertEqual(manifest["short_name"], "Coach AI")
        self.assertEqual(
            manifest["description"],
            "L'assistente AI che accompagna lo staff tecnico prima, durante e dopo ogni partita.",
        )
        self.assertEqual(manifest["start_url"], "/index.html?v=10530")
        self.assertIn('const CACHE_NAME = "matchiq-pwa-v138"', worker)
        self.assertIn('version: "10530"', app_meta)
        self.assertIn('const VERSION = "10530"', config)

    def test_live_and_scout_remain_available_as_direct_products(self):
        worker = read_frontend("service-worker.js")
        sitemap = read_frontend("sitemap.xml")

        for relative_path in ("live.html", "match.html", "scout.html", "js/live-page.js"):
            self.assertTrue((FRONTEND / relative_path).is_file(), relative_path)
        self.assertIn('"/live.html?v=10526"', worker)
        self.assertIn("/match.html", sitemap)
        self.assertIn("/scout.html", sitemap)


if __name__ == "__main__":
    unittest.main()
