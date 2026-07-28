import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.models.match_evidence import (
    MatchEvidenceFinalizeRequest,
    MatchEvidenceResponse,
)
from app.repositories import match_evidence_repository
from app.services import match_evidence_service


class MatchEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "match-evidence.db"
        self.original_connection = match_evidence_repository.get_connection
        self.original_use_postgres = match_evidence_repository.USE_POSTGRES

        def connection():
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            return conn

        match_evidence_repository.get_connection = connection
        match_evidence_repository.USE_POSTGRES = False
        conn = connection()
        conn.execute("CREATE TABLE users(id INTEGER PRIMARY KEY,email TEXT)")
        conn.executemany(
            "INSERT INTO users VALUES(?,?)",
            [(1, "one@test.it"), (2, "two@test.it")],
        )
        conn.commit()
        conn.close()
        match_evidence_service.initialize_match_evidence()

    def tearDown(self):
        match_evidence_repository.get_connection = self.original_connection
        match_evidence_repository.USE_POSTGRES = self.original_use_postgres
        self.tmp.cleanup()

    def request(self, score="2-1", report="Report iniziale"):
        return MatchEvidenceFinalizeRequest(
            source_match_id="coach-device-match-42",
            team_id="team-7",
            season_id="2026-2027",
            competition="Promozione",
            opponent="Rivale",
            match_date="2026-07-28",
            match={
                "result": {"score": score, "home_goals": 2, "away_goals": 1},
                "formation": {"home": "4-3-3", "away": "4-4-2"},
                "module": "4-3-3",
                "players": [{"id": "p1", "name": "Rossi", "role": "DC"}],
                "timeline_events": [{"id": "e1", "type": "gol", "minute": 12}],
                "substitutions": [],
                "cards": [],
                "goals": [{"id": "e1", "type": "gol", "minute": 12}],
            },
            coach={
                "notes": ["Alzare il baricentro"],
                "observations": ["transizione negativa"],
                "ratings": [{"playerId": "p1", "rating": 7}],
                "final_report": report,
            },
            voice_coach={"observation_ids": ["voice-11"]},
            video_ai={
                "video_report_ids": [91],
                "reviewed_frame_ids": ["frame-3"],
            },
            metadata={
                "coach_version": "10535",
                "schema_version": 1,
                "source": "coach_pwa",
                "flags": {"is_pwa": True},
            },
        )

    def test_creates_complete_match_evidence(self):
        item, created = match_evidence_service.finalize(1, self.request())

        self.assertTrue(created)
        self.assertTrue(item["canonical_match_id"].startswith("match_"))
        self.assertEqual(item["user_id"], 1)
        self.assertEqual(item["match"]["result"]["score"], "2-1")
        self.assertEqual(item["coach"]["final_report"], "Report iniziale")
        self.assertEqual(item["voice_coach"]["observation_ids"], ["voice-11"])
        self.assertEqual(item["video_ai"]["video_report_ids"], [91])

    def test_double_finalization_updates_without_duplicate(self):
        first, first_created = match_evidence_service.finalize(1, self.request())
        second, second_created = match_evidence_service.finalize(
            1,
            self.request(score="3-1", report="Report aggiornato"),
        )

        self.assertTrue(first_created)
        self.assertFalse(second_created)
        self.assertEqual(first["canonical_match_id"], second["canonical_match_id"])
        self.assertEqual(second["match"]["result"]["score"], "3-1")
        self.assertEqual(second["coach"]["final_report"], "Report aggiornato")
        self.assertEqual(len(match_evidence_service.list_for_user(1)), 1)

    def test_canonical_id_is_deterministic_and_user_scoped(self):
        first = match_evidence_service.canonical_match_id(1, "same-source")
        retry = match_evidence_service.canonical_match_id(1, "same-source")
        other_user = match_evidence_service.canonical_match_id(2, "same-source")

        self.assertEqual(first, retry)
        self.assertNotEqual(first, other_user)

    def test_retrieval_is_cross_device_and_owner_isolated(self):
        created, _ = match_evidence_service.finalize(1, self.request())

        loaded = match_evidence_service.get(1, created["canonical_match_id"])
        listed = match_evidence_service.list_for_user(1)

        self.assertEqual(loaded["source_match_id"], "coach-device-match-42")
        self.assertEqual(listed[0]["canonical_match_id"], created["canonical_match_id"])
        self.assertIsNone(match_evidence_service.get(2, created["canonical_match_id"]))
        self.assertEqual(match_evidence_service.list_for_user(2), [])

    def test_response_serialization_preserves_contract(self):
        item, _ = match_evidence_service.finalize(1, self.request())
        serialized = MatchEvidenceResponse(**item).model_dump(mode="json")

        self.assertEqual(serialized["schema_version"], 1)
        self.assertEqual(serialized["metadata"]["schema_version"], 1)
        self.assertIn("created_at", serialized)
        self.assertIn("finalized_at", serialized)
        self.assertIsInstance(serialized["match"]["timeline_events"], list)

    def test_coach_frontend_keeps_local_history_and_syncs_canonical_record(self):
        source = (
            Path(__file__).resolve().parents[1]
            / "frontend"
            / "js"
            / "coach-storage.js"
        ).read_text(encoding="utf-8")
        actions = (
            Path(__file__).resolve().parents[1]
            / "frontend"
            / "js"
            / "coach-actions.js"
        ).read_text(encoding="utf-8")

        self.assertIn("localStorage.setItem(HISTORY_KEY", source)
        self.assertIn('fetch("/api/match-evidence/finalize"', source)
        self.assertIn("ensureCoachSourceMatchId", source)
        create_block, finish_and_after = actions.split(
            "function finishCoachMatchDay()", 1
        )
        finish_block = finish_and_after.split(
            "function resetCoachLiveClock()", 1
        )[0]
        self.assertNotIn("finalizeCoachMatchEvidence()", create_block)
        self.assertIn("finalizeCoachMatchEvidence()", finish_block)
        self.assertLess(
            source.index("saveHistory(history)"),
            source.index("finalizeCoachMatchEvidence(item)"),
        )


if __name__ == "__main__":
    unittest.main()
