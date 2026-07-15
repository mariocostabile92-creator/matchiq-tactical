import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


def read(relative_path):
    return (FRONTEND / relative_path).read_text(encoding="utf-8")


class HomeTodayWorkspaceTests(unittest.TestCase):
    def test_today_sections_follow_the_product_order(self):
        home = read("index.html")
        section_ids = [
            "todayHero", "todayPriorities", "todayContinue", "nextMatch",
            "weeklyBriefing", "videoFocus", "weeklyFlow",
            "homeIntelligence", "recentWork",
        ]
        positions = [home.index(f'id="{section_id}"') for section_id in section_ids]
        self.assertEqual(positions, sorted(positions))

    def test_home_removes_old_dashboard_and_product_shortcuts(self):
        home = read("index.html")
        for text in ("Il tuo lavoro in numeri", "Quick Actions", "Video Hub"):
            self.assertNotIn(text, home)
        self.assertNotIn('href="/live.html', home)
        self.assertNotIn('href="/scout.html', home)
        self.assertNotIn("hubArchivePane", home)

    def test_primary_navigation_is_today_coach_video_and_account(self):
        config = read("js/global-nav-config.js")
        navigation = config.split("const navigation = [", 1)[1].split("];", 1)[0]
        for entry in (
            '{ key: "home", label: "Oggi"',
            '{ key: "coach", label: "Coach"',
            '{ key: "video", label: "Video AI"',
            '{ key: "account", label: "Account"',
        ):
            self.assertIn(entry, navigation)
        self.assertNotIn('key: "videoHub"', navigation)
        self.assertNotIn('key: "live"', navigation)
        self.assertNotIn('key: "scout"', navigation)

    def test_dynamic_focus_is_deterministic_and_priorities_are_limited(self):
        state = read("js/home-state.js")
        order = [
            "H.isMatchDayActive(current)",
            "H.isCoachWorkIncomplete(current)",
            "H.weeklyContext()&&!H.weeklyContext().isRead",
            'H.videoAttention()&&H.videoAttention().state!=="completed"',
            "H.trainingContext()?.needsAttention",
        ]
        positions = [state.index(token) for token in order]
        self.assertEqual(positions, sorted(positions))
        self.assertIn(".slice(0,4)", state)
        self.assertIn("String(today.hero.key)", state)

    def test_context_uses_real_local_match_and_hides_empty_continue(self):
        state = read("js/home-state.js")
        render = read("js/home-render.js")
        self.assertIn("H.nextMatchContext", state)
        self.assertIn("match.homeTeam", state)
        self.assertIn("match.awayTeam", state)
        self.assertIn("Tutto aggiornato.", render)
        self.assertIn("Nessuna partita programmata.", render)

    def test_home_fetches_each_context_source_once_without_side_effects(self):
        api = read("js/home-api.js")
        self.assertIn("Promise.allSettled", api)
        for endpoint in (
            "/api/account/limits", "/api/home/summary",
            "/api/weekly-briefing/current", "/api/training-planner/current",
        ):
            self.assertEqual(api.count(endpoint), 1, endpoint)
        self.assertNotIn("weekly-briefing/generate", api)

    def test_video_attention_order_and_no_fake_progress(self):
        state = read("js/home-state.js")
        render = read("js/home-render.js")
        tokens = ["const failed=", "const readyPriority=", "const processing=", "const completed="]
        positions = [state.index(token) for token in tokens]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("%", render)

    def test_weekly_flow_has_five_coaching_phases(self):
        render = read("js/home-render.js")
        for phase in ("Prepara", "Match Day", "Analizza", "Allena", "Riparti"):
            self.assertIn(f'["{phase}"', render)

    def test_intelligence_and_activity_are_coach_ai_scoped(self):
        render = read("js/home-render.js")
        state = read("js/home-state.js")
        for module in ("Pattern Intelligence", "Tactical Identity", "Decision Engine", "Club Intelligence"):
            self.assertIn(module, render)
        self.assertIn('item?.kind!=="scout_report"', state)
        self.assertIn('!module.includes("scout")', state)
        self.assertIn('!module.includes("live")', state)

    def test_club_intelligence_has_one_home_card_without_footer_banner(self):
        home = read("index.html")
        render = read("js/home-render.js")
        entry = read("js/club-intelligence-entry.js")
        self.assertEqual(render.count('"Club Intelligence"'), 1)
        self.assertNotIn("club-intelligence-entry", home)
        self.assertNotIn('path==="/"', entry)
        self.assertNotIn('"/index.html"', entry)
        for allowed_path in ("/account.html", "/knowledge.html", "/tactical-identity.html"):
            self.assertIn(allowed_path, entry)
        self.assertTrue((FRONTEND / "club-intelligence.html").is_file())

    def test_ai_disclaimer_is_unique_and_contextual(self):
        home = read("index.html")
        disclaimer = (
            "Le analisi e i suggerimenti generati dall'Intelligenza Artificiale "
            "rappresentano un supporto decisionale e devono essere sempre verificati dallo staff tecnico."
        )
        self.assertEqual(home.count(disclaimer), 1)
        intelligence = home.split('id="homeIntelligence"', 1)[1].split("</section>", 1)[0]
        self.assertIn('class="ai-disclaimer matchiq-disclaimer ai"', intelligence)
        self.assertIn('role="note"', intelligence)
        after_activity = home.split('id="recentWork"', 1)[1]
        self.assertNotIn("ai-disclaimer", after_activity)

    def test_final_spacing_keeps_activity_footer_and_api_scope(self):
        home = read("index.html")
        styles = read("css/home.css")
        meta = read("js/app-meta.js")
        api = read("js/home-api.js")
        self.assertIn('id="recentWork"', home)
        self.assertIn("#recentWork{margin-bottom:0}", styles)
        self.assertIn("#homeIntelligence>.ai-disclaimer.matchiq-disclaimer.ai", styles)
        self.assertIn("injectFooter()", meta)
        self.assertIn('footer.className = "matchiq-footer"', meta)
        for endpoint in (
            "/api/account/limits", "/api/home/summary",
            "/api/weekly-briefing/current", "/api/training-planner/current",
        ):
            self.assertEqual(api.count(endpoint), 1, endpoint)

    def test_today_is_pwa_first_and_accessible(self):
        home = read("index.html")
        styles = read("css/home.css")
        manifest = json.loads(read("manifest.json"))
        worker = read("service-worker.js")
        self.assertIn('class="skip-link"', home)
        self.assertIn('aria-live="polite"', home)
        self.assertIn("min-height:44px", styles)
        self.assertIn("safe-area-inset-top", styles)
        self.assertIn("safe-area-inset-bottom", styles)
        self.assertIn("focus-visible", styles)
        self.assertEqual(manifest["start_url"], "/index.html?v=10530")
        self.assertIn('const CACHE_NAME = "matchiq-pwa-v133"', worker)
        self.assertIn('"/css/home.css?v=10530"', worker)
        self.assertIn('caches.match("/index.html?v=10530")', worker)
        for asset in (
            "/js/app-meta.js?v=10530", "/css/global-nav.css?v=10530",
            "/js/auth.js?v=10530", "/js/global-nav-state.js?v=10530",
            "/js/weekly-briefing-state.js?v=10530", "/js/weekly-briefing-api.js?v=10530",
        ):
            self.assertIn(f'"{asset}"', worker)


if __name__ == "__main__":
    unittest.main()
