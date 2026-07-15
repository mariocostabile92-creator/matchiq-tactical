import re
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


CORE_PAGES = [
    "index.html",
    "account.html",
    "login.html",
    "register.html",
    "admin-analytics.html",
    "admin-beta.html",
    "admin-users.html",
    "coach.html",
    "match.html",
    "video.html",
    "scout.html",
    "weekly-briefing.html",
    "pattern-intelligence.html",
    "training-planner.html",
    "knowledge.html",
    "tactical-assistant.html",
    "tactical-identity.html",
    "decision-engine.html",
    "club-intelligence.html",
]


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.assets = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(values["id"])
        for key in ("src", "href"):
            value = values.get(key, "")
            if value.startswith("/") and not value.startswith("//"):
                self.assets.append(value)


class HardeningThreeTests(unittest.TestCase):
    def test_core_pages_exist_and_load_shared_meta(self):
        for name in CORE_PAGES:
            with self.subTest(page=name):
                source = (FRONTEND / name).read_text(encoding="utf-8")
                self.assertIn("<title>", source.lower())
                self.assertIn("app-meta.js", source)

    def test_core_pages_have_unique_ids(self):
        for name in CORE_PAGES:
            with self.subTest(page=name):
                parser = PageParser()
                parser.feed((FRONTEND / name).read_text(encoding="utf-8"))
                duplicates = sorted({item for item in parser.ids if parser.ids.count(item) > 1})
                self.assertEqual(duplicates, [])

    def test_literal_frontend_assets_referenced_by_core_pages_exist(self):
        missing = []
        asset_suffixes = {".html", ".css", ".js", ".json", ".png", ".jpg", ".jpeg", ".webp", ".svg", ".ico"}
        for name in CORE_PAGES:
            parser = PageParser()
            parser.feed((FRONTEND / name).read_text(encoding="utf-8"))
            for reference in parser.assets:
                literal = reference.split("?", 1)[0].split("#", 1)[0]
                if not literal or Path(literal).suffix.lower() not in asset_suffixes:
                    continue
                if not (FRONTEND / literal.lstrip("/")).exists():
                    missing.append(f"{name}: {literal}")
        self.assertEqual(missing, [])

    def test_release_and_cache_version_are_unique(self):
        manifest = (FRONTEND / "manifest.json").read_text(encoding="utf-8")
        app_meta = (FRONTEND / "js" / "app-meta.js").read_text(encoding="utf-8")
        video = (FRONTEND / "video.html").read_text(encoding="utf-8")
        worker = (FRONTEND / "service-worker.js").read_text(encoding="utf-8")
        self.assertIn('"start_url": "/index.html?v=10530"', manifest)
        self.assertIn('version: "10530"', app_meta)
        self.assertIn('const APP_VERSION = "10528"', video)
        self.assertIn('const CACHE_NAME = "matchiq-pwa-v131"', worker)

    def test_shared_navigation_covers_operational_modules(self):
        config = (FRONTEND / "js" / "global-nav-config.js").read_text(encoding="utf-8")
        app_meta = (FRONTEND / "js" / "app-meta.js").read_text(encoding="utf-8")
        for token in (
            "weekly-briefing",
            "pattern-intelligence",
            "training-planner",
            "knowledge",
            "tactical-assistant",
            "tactical-identity",
            "decision-engine",
            "club-intelligence",
        ):
            with self.subTest(module=token):
                self.assertIn(token, config)
        self.assertIn("injectGlobalNavigation", app_meta)
        self.assertIn("components.css", app_meta)
        self.assertIn("ux-hardening.js", app_meta)

    def test_shared_ux_has_recoverable_offline_error_table_and_dialog_states(self):
        script = (FRONTEND / "js" / "ux-hardening.js").read_text(encoding="utf-8")
        styles = (FRONTEND / "css" / "components.css").read_text(encoding="utf-8")
        for token in ("Riprova", "Sei offline", "unhandledrejection", "enhanceDialogs", "enhanceTables"):
            self.assertIn(token, script)
        for token in (".miq-table-scroll", "100dvh", "safe-area-inset-bottom", "prefers-reduced-motion"):
            self.assertIn(token, styles)

    def test_pwa_does_not_cache_private_or_large_generated_assets(self):
        worker = (FRONTEND / "service-worker.js").read_text(encoding="utf-8")
        self.assertIn('url.pathname.startsWith("/api/")', worker)
        self.assertIn("sensitiveExtension", worker)
        for extension in ("pdf", "mp4", "webm", "mp3", "wav", "csv"):
            self.assertIn(extension, worker)
        self.assertIn("staticExtension", worker)

    def test_coach_training_planner_uses_responsive_in_page_mount(self):
        coach = (FRONTEND / "coach.html").read_text(encoding="utf-8")
        script = (FRONTEND / "js" / "coach-training-planner.js").read_text(encoding="utf-8")
        styles = (FRONTEND / "css" / "coach.css").read_text(encoding="utf-8")
        self.assertEqual(coach.count('id="coachAiTrainingPlannerMount"'), 1)
        self.assertIn('getElementById("coachAiTrainingPlannerMount")', script)
        self.assertIn("#coachAiTrainingPlanner", styles)
        self.assertIn(".coach-training-plan-actions .btn", styles)
        self.assertIn("width:100%", styles)

    def test_coach_lineup_can_be_prepared_before_match_creation(self):
        coach = (FRONTEND / "coach.html").read_text(encoding="utf-8")
        actions = (FRONTEND / "js" / "coach-actions.js").read_text(encoding="utf-8")
        add_player = actions.split("function addLineupPlayer(){", 1)[1].split(
            "function deleteLineupPlayer", 1
        )[0]

        self.assertNotIn("if(!coachState.match)", add_player)
        self.assertIn("coachState.lineup.push(player)", add_player)
        self.assertIn(
            'type="button" onclick="addLineupPlayer()"',
            coach,
        )

    def test_coach_removes_redundant_five_step_onboarding(self):
        coach = (FRONTEND / "coach.html").read_text(encoding="utf-8")
        self.assertNotIn("Segui questi 5 step", coach)
        self.assertNotIn("coach-guide-card", coach)
        self.assertIn('id="coachPlanCard"', coach)

    def test_match_day_groups_team_events_without_changing_event_contracts(self):
        coach = (FRONTEND / "coach.html").read_text(encoding="utf-8")
        actions = (FRONTEND / "js" / "coach-actions.js").read_text(encoding="utf-8")
        render = (FRONTEND / "js" / "coach-render.js").read_text(encoding="utf-8")
        styles = (FRONTEND / "css" / "coach.css").read_text(encoding="utf-8")

        for element_id in ("coachLivePeriod", "coachLiveToggle", "coachVoiceBtn", "eventTeamInput"):
            self.assertEqual(coach.count(f'id="{element_id}"'), 1)
        self.assertEqual(coach.count("data-live-team-action"), 14)
        self.assertEqual(coach.count('data-team="home"'), 7)
        self.assertEqual(coach.count('data-team="away"'), 7)
        self.assertEqual(coach.count("data-tactical-event-label"), 8)
        self.assertEqual(coach.count("onclick=\"addLiveEvent("), 14)
        self.assertIn("NOTE E STRUMENTI STAFF", coach)
        self.assertIn("SQUADRA DI CASA", coach)
        self.assertIn("SQUADRA OSPITE", coach)

        self.assertIn('side:side || getInputValue("eventTeamInput", "home")', actions)
        self.assertIn('data-live-team-name', coach)
        self.assertIn('getTeamName(side)', render)
        self.assertIn('data-live-team-action', render)
        self.assertIn(".coach-team-events-grid", styles)
        self.assertIn("@media(max-width:760px)", styles)

    def test_tactical_assistant_footer_follows_conversation_content(self):
        page = (FRONTEND / "tactical-assistant.html").read_text(encoding="utf-8")
        layout = (FRONTEND / "css" / "tactical-assistant-layout.css").read_text(encoding="utf-8")
        worker = (FRONTEND / "service-worker.js").read_text(encoding="utf-8")

        self.assertIn("tactical-assistant-layout.css", page)
        self.assertIn("height: auto", layout)
        self.assertIn("overflow: visible", layout)
        self.assertIn("display-mode: standalone", layout)
        self.assertIn("/css/tactical-assistant-layout.css", worker)

    def test_pattern_refresh_keeps_a_stable_button_reference(self):
        script = (FRONTEND / "js" / "pattern-intelligence.js").read_text(encoding="utf-8")

        self.assertIn("const button=event.currentTarget;button.disabled=true", script)
        self.assertIn("finally{button.disabled=false}", script)
        self.assertNotIn("finally{event.currentTarget.disabled=false}", script)

    def test_home_groups_intelligence_modules_without_changing_routes(self):
        home = (FRONTEND / "index.html").read_text(encoding="utf-8")
        coordinator = (FRONTEND / "js" / "home-intelligence.js").read_text(encoding="utf-8")
        styles = (FRONTEND / "css" / "home-intelligence.css").read_text(encoding="utf-8")

        self.assertEqual(home.count('id="homeIntelligence"'), 1)
        self.assertEqual(home.count('id="homeIntelligenceGrid"'), 1)
        for selector in (
            "#weeklyHomeBanner",
            "#patternHome",
            "#tacticalIdentityEntry",
            "#decisionEngineEntry",
            ".club-intelligence-entry",
        ):
            self.assertIn(selector, coordinator)
        for route in (
            "/weekly-briefing.html",
            "/pattern-intelligence.html",
            "/tactical-identity.html",
            "/decision-engine.html",
            "/club-intelligence.html",
        ):
            sources = "\n".join(
                path.read_text(encoding="utf-8")
                for path in (FRONTEND / "js").glob("*.js")
            )
            self.assertIn(route, sources)
        self.assertIn("grid-template-columns:repeat(2,minmax(0,1fr))", styles)
        self.assertIn("@media(max-width:760px)", styles)
        self.assertIn(".intelligence-grid{grid-template-columns:1fr}", styles)

    def test_home_hero_represents_workspace_and_live_matches_stay_on_dedicated_page(self):
        home = (FRONTEND / "index.html").read_text(encoding="utf-8")
        state = (FRONTEND / "js" / "home-state.js").read_text(encoding="utf-8")
        render = (FRONTEND / "js" / "home-render.js").read_text(encoding="utf-8")
        api = (FRONTEND / "js" / "home-api.js").read_text(encoding="utf-8")
        actions = (FRONTEND / "js" / "home-actions.js").read_text(encoding="utf-8")

        self.assertIn("Oggi | MatchIQ Coach AI", home)
        self.assertIn("La scrivania digitale dell'allenatore.", home)
        self.assertIn("PRIORITÀ DI OGGI", home)
        self.assertNotIn("Partite live disponibili", home)
        self.assertNotIn("Partite live disponibili", state)
        for target in ("heroGreeting", "heroTitle", "heroLead"):
            self.assertNotIn(f'$("{target}").textContent', render)

        self.assertNotIn('id="liveMatchesSection"', home)
        self.assertNotIn('id="liveMatchesList"', home)
        self.assertNotIn("/api/live-matches", api)
        self.assertNotIn("loadLiveMatches", api)
        self.assertNotIn("data-live-", home)
        self.assertNotIn("data-live-", actions)
        self.assertNotIn('href="/live.html"', home)
        self.assertNotIn('href="/scout.html"', home)
        self.assertNotIn('href="/video.html#hubArchivePane"', home)
        live_page = (FRONTEND / "live.html").read_text(encoding="utf-8")
        live_script = (FRONTEND / "js" / "live-page.js").read_text(encoding="utf-8")
        scout_page = (FRONTEND / "scout.html").read_text(encoding="utf-8")
        self.assertIn('id="liveMatchesList"', live_page)
        self.assertIn("/api/live-matches", live_script)
        self.assertIn("/match.html?id=", live_script)
        self.assertIn("MatchIQ Scout", scout_page)

    def test_existing_pdf_download_contracts_remain_real_downloads(self):
        match_router = (ROOT / "app" / "routers" / "match.py").read_text(encoding="utf-8")
        video = (FRONTEND / "video.html").read_text(encoding="utf-8")
        coach = (FRONTEND / "js" / "coach-report.js").read_text(encoding="utf-8")
        self.assertIn('media_type="application/pdf"', match_router)
        self.assertIn("filename=filename", match_router)
        self.assertIn('type:"application/pdf"', video)
        self.assertIn("a.download = `${title}.pdf`", video)
        self.assertIn('window.open("", "_blank"', coach)
        self.assertIn("printWindow.print()", coach)


if __name__ == "__main__":
    unittest.main()
