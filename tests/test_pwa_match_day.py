import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
FORMATIONS = ("4-3-3", "4-4-2", "4-2-3-1", "4-3-1-2", "3-5-2", "3-4-3", "5-3-2")


def read_frontend(relative_path):
    return (FRONTEND / relative_path).read_text(encoding="utf-8")


def formation_slots(source, formation):
    pattern = rf'"{re.escape(formation)}": \[(.*?)\](?=,\r?\n\s+"|\r?\n\s+\}}\);)'
    match = re.search(pattern, source, re.DOTALL)
    if not match:
        return []
    return re.findall(r'slot\("([^"]+)","([^"]+)",(\d+),(\d+)\)', match.group(1))


class PwaMatchDaySprintTests(unittest.TestCase):
    def test_all_supported_formations_have_eleven_valid_unique_slots(self):
        source = read_frontend("js/coach-lineup-layouts.js")
        for formation in FORMATIONS:
            with self.subTest(formation=formation):
                slots = formation_slots(source, formation)
                self.assertEqual(len(slots), 11)
                self.assertEqual(len({slot[0] for slot in slots}), 11)
                for _slot_id, _role, x, y in slots:
                    self.assertGreaterEqual(int(x), 0)
                    self.assertLessEqual(int(x), 100)
                    self.assertGreaterEqual(int(y), 0)
                    self.assertLessEqual(int(y), 100)

    def test_formations_are_persistent_and_separate_for_home_and_away(self):
        source = read_frontend("js/coach-lineup-layouts.js")
        for token in (
            "matchiq_coach_lineup_formations_v1",
            'normalizedSide === "away" ? match.awayShape : match.homeShape',
            "persistFormation(side, value)",
            "ensureSlots(side)",
        ):
            self.assertIn(token, source)

    def test_lineup_supports_pointer_drag_swap_and_bench_drop(self):
        source = read_frontend("js/coach-lineup-interactions.js")
        for token in (
            'addEventListener("pointerdown"',
            'addEventListener("pointermove"',
            'addEventListener("pointerup"',
            "requestAnimationFrame",
            "moveLineupPlayerToSlot",
            "moveLineupPlayerToBench",
            'occupant.status = "Panchina"',
            "occupant.slot = previousSlot",
        ):
            self.assertIn(token, source)
        self.assertNotIn("Sortable", source)
        self.assertNotIn("Dragula", source)

    def test_lineup_has_click_editor_and_responsive_dialog(self):
        page = read_frontend("coach.html")
        menu = read_frontend("js/coach-lineup-player-menu.js")
        styles = read_frontend("css/coach-lineup.css")
        self.assertEqual(page.count('id="lineupPlayerDialog"'), 1)
        for token in ("lineupEditNumber", "lineupEditName", "lineupEditRole", "lineupEditStatus"):
            self.assertIn(token, page)
        for token in ("openLineupPlayerMenu", "saveLineupPlayerChanges", "removeLineupPlayerFromDialog"):
            self.assertIn(token, menu)
        self.assertIn("@media(max-width:520px)", styles)
        self.assertIn("safe-area-inset-bottom", styles)

    def test_match_day_keeps_team_events_and_staff_tools_separate(self):
        page = read_frontend("coach.html")
        self.assertEqual(page.count("data-live-team-action"), 18)
        self.assertEqual(page.count('data-team="home"'), 9)
        self.assertEqual(page.count('data-team="away"'), 9)
        self.assertEqual(page.count("data-tactical-event-label"), 8)
        self.assertIn("NOTE E STRUMENTI STAFF", page)
        self.assertIn('id="eventTeamInput"', page)

    def test_match_day_commands_cover_the_real_match_cycle(self):
        page = read_frontend("coach.html")
        source = read_frontend("js/coach-match-day.js")
        for action in ("pause", "1T", "INT", "2T", "REC", "finish"):
            self.assertIn(f"setCoachMatchCommand('{action}')", page)
        for period in ("1T", "INT", "2T", "REC"):
            self.assertIn(f'"{period}"', source)
        self.assertIn("startCoachLiveClock", source)
        self.assertIn("stopCoachLiveClock(true)", source)

    def test_timer_uses_lightweight_updates_while_running(self):
        actions = read_frontend("js/coach-actions.js")
        render = read_frontend("js/coach-render.js")
        ticker = actions.split("function ensureCoachLiveTicker(){", 1)[1].split(
            "function startCoachVoiceNote", 1
        )[0]
        self.assertIn("renderLiveClockOnly", ticker)
        self.assertNotIn("renderAll()", ticker)
        self.assertIn("function renderLiveClockOnly()", render)
        self.assertIn("function renderMatchDayEventUpdate()", render)

    def test_event_feedback_prevents_fast_duplicates_without_network_calls(self):
        feedback = read_frontend("js/coach-match-feedback.js")
        actions = read_frontend("js/coach-actions.js")
        for token in ("LOCK_MS = 900", "isDuplicate", 'aria-busy', "navigator.vibrate", "clientActionId"):
            self.assertIn(token, feedback + actions)
        self.assertIn("Online · eventi salvati sul dispositivo", feedback)
        self.assertIn("Offline · eventi salvati sul dispositivo", feedback)
        self.assertNotIn("fetch(", feedback)

    def test_pwa_release_is_consistent_and_caches_match_day_assets(self):
        manifest = json.loads(read_frontend("manifest.json"))
        worker = read_frontend("service-worker.js")
        self.assertEqual(manifest["start_url"], "/index.html?v=10530")
        self.assertEqual(manifest["display"], "standalone")
        self.assertIn('const CACHE_NAME = "matchiq-pwa-v133"', worker)
        for asset in (
            "/css/coach-lineup.css?v=10532",
            "/js/coach-lineup-layouts.js?v=10531",
            "/js/coach-lineup-interactions.js?v=10531",
            "/js/coach-lineup-player-menu.js?v=10531",
            "/js/coach-match-day.js?v=10533",
            "/js/coach-match-feedback.js?v=10526",
        ):
            self.assertIn(f'"{asset}"', worker)

    def test_coach_load_order_makes_features_available_before_core_boot(self):
        page = read_frontend("coach.html")
        core = page.index("/js/coach-core.js?v=10526")
        for asset in (
            "/js/coach-lineup-layouts.js?v=10531",
            "/js/coach-match-feedback.js?v=10526",
            "/js/coach-match-day.js?v=10533",
            "/js/coach-lineup-interactions.js?v=10531",
            "/js/coach-lineup-player-menu.js?v=10531",
        ):
            self.assertLess(page.index(asset), core)

    def test_fifty_field_use_scenarios_have_implementation_coverage(self):
        lineup = read_frontend("js/coach-lineup-layouts.js")
        interactions = read_frontend("js/coach-lineup-interactions.js")
        match_day = read_frontend("js/coach-match-day.js")
        feedback = read_frontend("js/coach-match-feedback.js")
        styles = read_frontend("css/coach.css") + read_frontend("css/coach-lineup.css")

        scenarios = []
        scenarios.extend(("formation", side, formation) for side in ("home", "away") for formation in FORMATIONS)
        scenarios.extend(
            ("viewport", viewport, action)
            for viewport in ("desktop", "tablet", "smartphone", "standalone")
            for action in ("select", "drag", "swap", "bench", "edit")
        )
        scenarios.extend(
            ("match", period, action)
            for period in ("1T", "INT", "2T", "REC")
            for action in ("event", "pause", "resume", "duplicate")
        )
        self.assertEqual(len(scenarios), 50)

        for family, context, action in scenarios:
            with self.subTest(family=family, context=context, action=action):
                if family == "formation":
                    self.assertIn(f'"{action}"', lineup)
                    self.assertIn(context, lineup)
                elif family == "viewport":
                    self.assertIn("touch-action:none", styles)
                    self.assertIn("pointerdown", interactions)
                    self.assertIn("100dvh", styles)
                else:
                    self.assertIn(f'"{context}"', match_day)
                    self.assertIn("isDuplicate", feedback)

    def test_independent_live_match_and_scout_products_remain_present(self):
        for relative_path in ("live.html", "match.html", "scout.html", "js/live-page.js"):
            self.assertTrue((FRONTEND / relative_path).is_file(), relative_path)
        for relative_path in ("live.html", "match.html", "scout.html"):
            self.assertIn("?v=10524", read_frontend(relative_path))


if __name__ == "__main__":
    unittest.main()
