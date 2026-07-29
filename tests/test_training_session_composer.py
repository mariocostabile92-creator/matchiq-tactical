import unittest

from app.services.training_session_composer import compose_session


def proposal(
    priority_id="priority-1",
    topic="pressing",
    intensity="media",
    drills=True,
):
    return {
        "priority_id": priority_id,
        "topic": topic,
        "title": "Pressing coordinato",
        "references": {
            "canonical_match_ids": ["match-1"],
            "pattern_ids": [11],
            "evidence_ids": [21],
        },
        "drills": (
            [
                {
                    "id": 7,
                    "title": "Pressing in zona",
                    "tactical_theme": topic,
                    "intensity": intensity,
                    "duration": 20,
                }
            ]
            if drills
            else []
        ),
    }


class TrainingSessionComposerTest(unittest.TestCase):
    def settings(self, **overrides):
        values = {
            "players": 18,
            "goalkeepers": 2,
            "session_duration": 90,
            "intensity": "media",
            "category": "Dilettanti",
            "training_days": ["Martedì", "Giovedì"],
        }
        values.update(overrides)
        return values

    def profile(self, **overrides):
        values = {
            "category": "Dilettanti",
            "level": "Prima squadra",
            "average_age": 24.5,
            "player_count": 18,
            "goalkeeper_count": 2,
            "training_days": ["Martedì", "Giovedì"],
            "training_duration": 90,
            "match_day": "Domenica",
            "pitch_type": "Sintetico",
            "pitch_dimensions": "100 x 60 m",
            "available_materials": ["Palloni", "Cinesini"],
            "playing_principles": ["Pressing orientato"],
            "preferred_formation": "4-3-3",
            "average_intensity": "media",
            "season_objectives": ["Sviluppo giovani"],
        }
        values.update(overrides)
        return values

    def test_composes_one_professional_session_from_existing_library(self):
        result = compose_session(
            [proposal()],
            self.settings(),
            self.profile(),
            ["Martedì", "Giovedì"],
        )
        session = result["sessions"][0]

        self.assertEqual(result["contract"], "weekly-priority-session-composer-v2")
        self.assertEqual(len(session["blocks"]), 6)
        self.assertEqual(sum(item["duration"] for item in session["blocks"]), 90)
        self.assertEqual(session["drills"][0]["id"], 7)
        self.assertEqual(session["drills"][0]["composer_block"], "themed_match")
        self.assertEqual(result["decisions"][0]["status"], "SCHEDULED")
        self.assertEqual(
            result["explainability"]["chain"],
            ["Pattern", "Priorità", "Decisione", "Seduta"],
        )
        self.assertEqual(result["team_profile"]["preferred_formation"], "4-3-3")

    def test_defers_priority_without_compatible_library_drill(self):
        result = compose_session(
            [proposal(drills=False)],
            self.settings(),
            self.profile(),
            ["Martedì"],
        )
        session = result["sessions"][0]

        self.assertEqual(result["decisions"][0]["status"], "DEFERRED")
        self.assertEqual(session["priority_ids"], [])
        self.assertEqual(session["drills"], [])
        self.assertIn("1 priorità rinviate", session["why"])

    def test_defers_high_load_on_day_before_match(self):
        result = compose_session(
            [proposal(intensity="alta")],
            self.settings(intensity="alta"),
            self.profile(match_day="Domenica", average_intensity="alta"),
            ["Sabato"],
        )

        self.assertEqual(result["calendar_context"]["days_to_match"], 1)
        self.assertEqual(result["calendar_context"]["load_strategy"], "rifinitura")
        self.assertEqual(result["decisions"][0]["status"], "DEFERRED")
        self.assertIn("giorno precedente", result["decisions"][0]["reason"])

    def test_keeps_structured_references_without_inventing_sources(self):
        result = compose_session(
            [proposal()],
            self.settings(),
            self.profile(),
            ["Martedì"],
        )
        references = result["sessions"][0]["references"]

        self.assertEqual(references["canonical_match_ids"], ["match-1"])
        self.assertEqual(references["pattern_ids"], [11])
        self.assertEqual(references["evidence_ids"], [21])
        self.assertEqual(
            result["decisions"][0]["canonical_match_ids"],
            ["match-1"],
        )


if __name__ == "__main__":
    unittest.main()
