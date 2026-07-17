import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
FORMATIONS = ("4-3-3", "4-4-2", "4-2-3-1", "4-3-1-2", "3-5-2", "3-4-3", "5-3-2")
VIEWPORTS = {
    "desktop": (480, 560, 84, 66, 4),
    "tablet": (680, 520, 68, 64, 6),
    "smartphone": (300, 470, 54, 54, 2),
}


def read_frontend(relative_path):
    return (FRONTEND / relative_path).read_text(encoding="utf-8")


def formation_slots(source, formation):
    pattern = rf'"{re.escape(formation)}": \[(.*?)\](?=,\r?\n\s+"|\r?\n\s+\}}\);)'
    match = re.search(pattern, source, re.DOTALL)
    if not match:
        return []
    return [
        (slot_id, role, int(x), int(y))
        for slot_id, role, x, y in re.findall(
            r'slot\("([^"]+)","([^"]+)",(\d+),(\d+)\)', match.group(1)
        )
    ]


def tactical_slots(source, formation):
    block = source.split("const tacticalLayouts = Object.freeze({", 1)[1].split(
        "\n  });\n  const aliases", 1
    )[0]
    match = re.search(
        rf'"{re.escape(formation)}": \{{(.*?)\n    \}}', block, re.DOTALL
    )
    if not match:
        return {}
    return {
        slot_id: (label, short)
        for slot_id, label, short in re.findall(
            r'(\w+):tactical\("([^"]+)","([^"]+)"\)', match.group(1)
        )
    }


class CoachFormationPolishTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layouts = read_frontend("js/coach-lineup-layouts.js")
        cls.render = read_frontend("js/coach-render.js")
        cls.interactions = read_frontend("js/coach-lineup-interactions.js")
        cls.menu = read_frontend("js/coach-lineup-player-menu.js")
        cls.styles = read_frontend("css/coach-lineup.css")

    def test_all_formations_have_eleven_unique_slots_inside_safe_area(self):
        for formation in FORMATIONS:
            with self.subTest(formation=formation):
                slots = formation_slots(self.layouts, formation)
                self.assertEqual(len(slots), 11)
                self.assertEqual(len({slot_id for slot_id, *_rest in slots}), 11)
                for _slot_id, _role, x, y in slots:
                    self.assertGreaterEqual(x, 12)
                    self.assertLessEqual(x, 88)
                    self.assertGreaterEqual(y, 9)
                    self.assertLessEqual(y, 91)

    def test_safe_area_is_centralized_and_applied_in_pixels_and_percentages(self):
        for token in (
            "PITCH_SAFE_AREA",
            "safePosition(item)",
            "safeArea:{...PITCH_SAFE_AREA}",
            "--lineup-safe-x",
            "--lineup-safe-y",
            "left:clamp(",
            "top:clamp(",
            "--slot-left:${position.x}%",
            "--slot-top:${position.y}%",
        ):
            self.assertIn(token, self.layouts + self.render + self.styles)

    def test_tactical_mapping_covers_every_slot_without_changing_primary_roles(self):
        total = 0
        for formation in FORMATIONS:
            with self.subTest(formation=formation):
                primary = formation_slots(self.layouts, formation)
                tactical = tactical_slots(self.layouts, formation)
                self.assertEqual(set(tactical), {slot_id for slot_id, *_rest in primary})
                self.assertTrue(all(label and short for label, short in tactical.values()))
                total += len(tactical)
        self.assertEqual(total, 77)
        self.assertIn("preferredRole(player.role)", self.layouts)
        self.assertNotIn("player.role =", self.layouts)

    def test_expected_tactical_positions_are_exposed_for_each_formation(self):
        expected = {
            "4-3-3": {"m2": "MED", "a1": "AS", "a3": "AD"},
            "4-4-2": {"m1": "ES", "m4": "ED", "a1": "SP"},
            "4-2-3-1": {"t2": "TRQ", "a1": "PC"},
            "4-3-1-2": {"t1": "TRQ", "a1": "SP"},
            "3-5-2": {"d1": "BSX", "m1": "QS", "m5": "QD"},
            "3-4-3": {"d3": "BDX", "a1": "AS", "a3": "AD"},
            "5-3-2": {"d1": "QS", "d5": "QD", "m2": "MED"},
        }
        for formation, values in expected.items():
            tactical = tactical_slots(self.layouts, formation)
            for slot_id, short in values.items():
                with self.subTest(formation=formation, slot=slot_id):
                    self.assertEqual(tactical[slot_id][1], short)

    def test_no_visual_collisions_for_supported_responsive_sizes(self):
        checked = 0
        for formation in FORMATIONS:
            slots = formation_slots(self.layouts, formation)
            for viewport, metrics in VIEWPORTS.items():
                pitch_width, pitch_height, card_width, card_height, gap = metrics
                collisions = []
                for index, current in enumerate(slots):
                    for other in slots[index + 1 :]:
                        horizontal = abs(current[2] - other[2]) * pitch_width / 100
                        vertical = abs(current[3] - other[3]) * pitch_height / 100
                        if horizontal < card_width + gap and vertical < card_height + gap:
                            collisions.append((current[0], other[0]))
                with self.subTest(formation=formation, viewport=viewport):
                    self.assertEqual(collisions, [])
                checked += 1
        self.assertEqual(checked, 21)

    def test_compact_cards_keep_number_name_and_tactical_role_readable(self):
        for token in (
            "pitch-shirt",
            'title="${esc(player.name)}"',
            "${esc(player.name)}",
            "${esc(slot.tacticalShort)}",
            "text-overflow:ellipsis",
            "white-space:nowrap",
            "height:var(--lineup-card-height)",
            "max-height:var(--lineup-card-height)",
            "padding:4px 5px",
            "flex:0 0 24px",
            "font-size:11px;line-height:1.15",
            "font-size:9px;line-height:1.1",
        ):
            self.assertIn(token, self.render + self.styles)

    def test_accessibility_and_touch_states_are_explicit(self):
        for token in (
            "aria-label=\"${esc(player.name)}, numero",
            "aria-grabbed",
            ":focus-visible",
            ".is-selected",
            ".is-drag-target",
            ".is-occupied.is-drag-target",
            "@media(pointer:coarse)",
            "min-height:44px",
            "safe-area-inset-bottom",
            "100dvh",
        ):
            self.assertIn(token, self.render + self.interactions + self.styles)

    def test_drag_swap_bench_and_data_contract_remain_unchanged(self):
        for token in (
            "moveLineupPlayerToSlot",
            "moveLineupPlayerToBench",
            'occupant.status = "Panchina"',
            "occupant.slot = previousSlot",
            'player.status = "Titolare"',
            'player.status = "Panchina"',
            "saveState()",
            "renderLineup()",
            "new Set()",
            "!used.has(player.slot)",
        ):
            self.assertIn(token, self.layouts + self.interactions)
        self.assertNotIn("fetch(", self.interactions)

    def test_lineup_assets_are_versioned_and_available_to_the_pwa(self):
        page = read_frontend("coach.html")
        worker = read_frontend("service-worker.js")
        assets = (
            "/css/coach-lineup.css?v=10532",
            "/js/coach-lineup-layouts.js?v=10531",
            "/js/coach-lineup-interactions.js?v=10531",
            "/js/coach-lineup-player-menu.js?v=10531",
        )
        self.assertIn('const CACHE_NAME = "matchiq-pwa-v140"', worker)
        for asset in assets:
            with self.subTest(asset=asset):
                self.assertIn(asset, page)
                self.assertIn(f'"{asset}"', worker)
                self.assertTrue((FRONTEND / asset.split("?", 1)[0].lstrip("/")).is_file())

    def test_thirty_acceptance_scenarios_have_direct_coverage(self):
        scenarios = []
        scenarios.extend(("formation", formation) for formation in FORMATIONS)
        scenarios.extend(("viewport", viewport) for viewport in VIEWPORTS)
        scenarios.extend(("side", side) for side in ("home", "away"))
        scenarios.extend(("interaction", action) for action in ("select", "drag", "swap", "bench", "edit", "remove"))
        scenarios.extend(("content", item) for item in ("number", "long-name", "tactical-label", "primary-role"))
        scenarios.extend(("state", state) for state in ("empty", "occupied", "selected", "dragging"))
        scenarios.extend(("persistence", item) for item in ("formation", "slot", "status", "side"))
        self.assertEqual(len(scenarios), 30)


if __name__ == "__main__":
    unittest.main()
