import sqlite3
import sys
import tempfile
import types
import unittest
from pathlib import Path

try:
    import psycopg2  # noqa: F401
except ModuleNotFoundError:
    pg = types.ModuleType("psycopg2")
    extras = types.ModuleType("psycopg2.extras")
    extras.RealDictCursor = object
    pg.extras = extras
    sys.modules["psycopg2"] = pg
    sys.modules["psycopg2.extras"] = extras

from app.models.voice_coach_intelligence import VoiceObservationCreate
from app.repositories import knowledge_repository, voice_coach_repository
from app.services import knowledge_service, voice_coach_intelligence_service
from app.services.voice_coach_schemas import VoiceCoachInterpretRequest, VoiceCoachMatchContext, VoiceCoachPlayer
from app.services.voice_coach_service import interpret_voice_coach_command
from app.services.voice_coach_intelligence_service import enrich_interpretation
from app.services.voice_coach_taxonomy import classify_tactical_topic


class VoiceCoachIntelligenceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "voice.db"
        self.original = {
            "knowledge_conn": knowledge_repository.get_connection,
            "knowledge_pg": knowledge_repository.USE_POSTGRES,
            "voice_conn": voice_coach_repository.get_connection,
            "voice_pg": voice_coach_repository.USE_POSTGRES,
        }

        def connection():
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            return conn

        knowledge_repository.get_connection = connection
        knowledge_repository.USE_POSTGRES = False
        voice_coach_repository.get_connection = connection
        voice_coach_repository.USE_POSTGRES = False
        conn = connection()
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT NOT NULL)")
        conn.executemany("INSERT INTO users (id, email) VALUES (?, ?)", [(1, "one@test.it"), (2, "two@test.it")])
        conn.commit()
        conn.close()
        knowledge_service.initialize_foundation()
        voice_coach_intelligence_service.initialize_voice_coach_intelligence()

    def tearDown(self):
        knowledge_repository.get_connection = self.original["knowledge_conn"]
        knowledge_repository.USE_POSTGRES = self.original["knowledge_pg"]
        voice_coach_repository.get_connection = self.original["voice_conn"]
        voice_coach_repository.USE_POSTGRES = self.original["voice_pg"]
        self.tmp.cleanup()

    def _context(self):
        return VoiceCoachMatchContext(
            match_id="match-1", home_team="MatchIQ", away_team="Rivali", current_minute=34, period="1T",
            lineup=[
                VoiceCoachPlayer(id="10", number="10", name="Marco Rossi", aliases=["Marcolino"], side="home", status="Titolare"),
                VoiceCoachPlayer(id="8", number="8", name="Luca Rossi", side="home", status="Titolare"),
            ],
            bench=[VoiceCoachPlayer(id="18", number="18", name="Paolo Bianchi", side="home", status="Panchina")],
        )

    def _interpret(self, text):
        request = VoiceCoachInterpretRequest(transcript=text, source="text", context=self._context())
        return enrich_interpretation(interpret_voice_coach_command(request), request)

    def _observation(self, client_id, text, minute, topic="second_post", zone="area", user=1):
        payload = VoiceObservationCreate(
            client_id=client_id, match_key="match-1", match_id="match-1", intent="tactical_note",
            confidence=0.88, original_text=text, normalized_summary=text, minute=minute, match_phase="1T",
            team="home", tactical_topic=topic, topic_label="Secondo palo" if topic == "second_post" else "Pressing",
            zone=zone, polarity="negative", priority="high", source="text", evidence=["Test"], status="confirmed",
        )
        return voice_coach_intelligence_service.save_observation(user, payload)

    def test_contextual_interpretation_and_real_player_resolution(self):
        result = self._interpret("Marcolino sta giocando bene al minuto 35")
        self.assertEqual(result.intent, "player_note")
        self.assertEqual(result.entities["player_id"], "10")
        self.assertEqual(result.tactical_topic, "positive_behavior")
        self.assertTrue(result.explanation)
        self.assertTrue(result.evidence)

        ambiguous = self._interpret("Rossi e stanco")
        self.assertTrue(ambiguous.requires_confirmation)
        self.assertTrue(any("ambiguo" in item.lower() for item in ambiguous.ambiguities))

        missing = self._interpret("Verdi e stanco")
        self.assertFalse(missing.entities.get("player_id"))
        self.assertNotIn("Verdi", str(missing.entities.get("player_name")))

        full_name = self._interpret("Marco Rossi e stanco")
        self.assertEqual(full_name.entities["player_id"], "10")

        bench_request = VoiceCoachInterpretRequest(
            transcript="Paolo Bianchi e stanco", source="text", context=self._context()
        )
        bench = enrich_interpretation(interpret_voice_coach_command(bench_request), bench_request)
        self.assertEqual(bench.entities["player_id"], "18")

    def test_tactical_phrases_and_clarification(self):
        expected = {
            "Stiamo soffrendo a destra": "right_flank",
            "Secondo palo libero": "second_post",
            "Pressiamo troppo bassi": "pressing",
            "Stiamo uscendo bene dal basso": "build_up",
            "Marco sta giocando bene": "positive_behavior",
        }
        for phrase, topic in expected.items():
            self.assertEqual(classify_tactical_topic(phrase)["topic"], topic)
        vague = self._interpret("Stiamo soffrendo")
        self.assertTrue(vague.clarification_question)
        self.assertIn("Salva senza specificare", vague.clarification_options)

    def test_events_changes_score_cancel_and_minute(self):
        cases = {
            "Gol nostro di Marco Rossi al minuto 22": "player_event",
            "Tiro di Marco Rossi": "player_event",
            "Grande recupero di Marco Rossi": "player_event",
            "Palla persa da Marco Rossi": "player_event",
            "Giallo a Marco Rossi": "player_event",
            "Cambio Marco Rossi per Paolo Bianchi": "substitution",
            "Siamo due a uno": "score_update",
            "Annulla": "cancel",
        }
        for phrase, intent in cases.items():
            result = self._interpret(phrase)
            self.assertEqual(result.intent, intent, phrase)
        minute = self._interpret("Secondo palo libero al minuto 28")
        self.assertEqual(minute.minute, 28)

    def test_recurring_themes_are_semantic_idempotent_and_isolated(self):
        self._observation("obs-a", "Secondo palo libero", 18)
        self._observation("obs-b", "Ancora scoperti sul palo dietro", 31)
        result = self._observation("obs-c", "Dietro sul secondo palo siamo in difficolta", 41)
        result = self._observation("obs-c", "Dietro sul secondo palo siamo in difficolta", 41)
        self.assertEqual(len(result["themes"]), 1)
        self.assertEqual(result["themes"][0]["count"], 3)
        self.assertEqual(result["themes"][0]["first_minute"], 18)
        self.assertEqual(result["themes"][0]["last_minute"], 41)
        intelligence = voice_coach_intelligence_service.match_intelligence(1, "match-1")
        self.assertEqual(len(intelligence["observations"]), 3)
        self.assertTrue(any(item["type"] == "recurring_theme" for item in intelligence["proactive_suggestions"]))
        self.assertEqual(voice_coach_intelligence_service.match_intelligence(2, "match-1")["observations"], [])

    def test_knowledge_link_and_cancel_do_not_change_profiles(self):
        self._observation("source-1", "Secondo palo libero", 20)
        knowledge = knowledge_service.get_knowledge(1)
        self.assertIsNone(knowledge.coach_profile.coach_name)
        self.assertIsNone(knowledge.team_profile.category)
        self.assertEqual(len(knowledge.source_links), 1)
        cancelled = voice_coach_intelligence_service.cancel_observation(1, "source-1")
        self.assertEqual(cancelled["status"], "cancelled")
        self.assertEqual(knowledge_service.get_knowledge(1).source_links, [])

    def test_different_topics_do_not_merge(self):
        self._observation("obs-x", "Secondo palo libero", 12)
        result = self._observation("obs-y", "Pressiamo troppo bassi", 14, topic="pressing", zone="central")
        self.assertEqual(len(result["themes"]), 2)

    def test_match_deletion_removes_observations_and_knowledge_sources(self):
        self._observation("delete-me", "Secondo palo libero", 12)
        self.assertEqual(len(knowledge_service.get_knowledge(1).source_links), 1)
        deleted = voice_coach_intelligence_service.delete_match_intelligence(1, "match-1")
        self.assertEqual(deleted, 1)
        self.assertEqual(voice_coach_intelligence_service.match_intelligence(1, "match-1")["observations"], [])
        self.assertEqual(knowledge_service.get_knowledge(1).source_links, [])


if __name__ == "__main__":
    unittest.main()
