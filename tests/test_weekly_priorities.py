import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path

from app.repositories import (
    knowledge_repository,
    pattern_intelligence_repository,
    training_planner_repository,
    weekly_priority_repository,
)
from app.services import (
    knowledge_service,
    pattern_intelligence_service,
    training_planner_service,
    weekly_priority_service,
)


class WeeklyPriorityServiceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "weekly-priorities.db"
        self.originals = []

        def connection():
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            return conn

        for module in (
            knowledge_repository,
            pattern_intelligence_repository,
            training_planner_repository,
            weekly_priority_repository,
        ):
            self.originals.append(
                (
                    module,
                    getattr(module, "get_connection", None),
                    getattr(module, "USE_POSTGRES", None),
                )
            )
            if hasattr(module, "get_connection"):
                module.get_connection = connection
            if hasattr(module, "USE_POSTGRES"):
                module.USE_POSTGRES = False

        conn = connection()
        conn.execute("CREATE TABLE users(id INTEGER PRIMARY KEY,email TEXT)")
        conn.executemany(
            "INSERT INTO users VALUES(?,?)",
            [(1, "one@test.it"), (2, "two@test.it")],
        )
        conn.commit()
        conn.close()

        knowledge_service.initialize_foundation()
        pattern_intelligence_service.initialize_pattern_intelligence()
        weekly_priority_service.initialize_weekly_priorities()
        training_planner_service.initialize_training_planner()
        self.workspace = knowledge_repository.get_or_create_workspace(1)

    def tearDown(self):
        for module, connection, use_postgres in self.originals:
            if connection is not None:
                module.get_connection = connection
            if use_postgres is not None:
                module.USE_POSTGRES = use_postgres
        self.tmp.cleanup()

    def pattern(
        self,
        *,
        topic="transition_defense",
        title="Protezione dopo la perdita",
        phase="negative_transition",
        confidence=82,
        matches=3,
        occurrence=0.75,
        status="established",
        source_prefix="coach",
    ):
        today = date.today().isoformat()
        evidence = []
        for index in range(1, matches + 1):
            source_type = {
                1: "match_evidence_coach_event",
                2: "voice_coach_observation",
                3: "video_frame_feedback",
            }.get(index, source_prefix)
            evidence.append(
                {
                    "source_type": source_type,
                    "source_id": f"{source_prefix}-{topic}-{index}",
                    "match_id": f"match-{index}",
                    "minute": 20 + index,
                    "event_type": "palla_persa",
                    "player_id": None,
                    "topic": topic,
                    "zone": "central",
                    "phase": phase,
                    "formation": "4-3-3",
                    "polarity": "negative",
                    "evidence_summary": f"Evidenza {index}",
                    "evidence_weight": 0.9,
                    "objective_or_subjective": "objective",
                    "created_at": today,
                }
            )
        return {
            "canonical_topic": topic,
            "title": title,
            "normalized_summary": title,
            "category": "tactical",
            "polarity": "negative",
            "zone": "central",
            "phase": phase,
            "context_player_id": None,
            "frequency_count": matches,
            "matches_count": matches,
            "matches_total": matches + 1,
            "occurrence_rate": occurrence,
            "first_seen_at": today,
            "last_seen_at": today,
            "trend_direction": "in aumento",
            "confidence_score": confidence,
            "confidence_level": "high" if confidence >= 75 else "medium",
            "severity": "alta",
            "status": status,
            "explanation": "Pattern ricorrente verificabile.",
            "limitations": [],
            "source_classes": {"coach": matches},
            "contradictory": False,
            "evidence": evidence,
        }

    def save_run(self, patterns):
        today = date.today().isoformat()
        run = pattern_intelligence_repository.create_run(
            1,
            int(self.workspace["id"]),
            None,
            today,
            today,
            3,
            ["match_evidence"],
            f"fingerprint-{len(patterns)}-{patterns[0]['canonical_topic']}",
            "test-v1",
        )
        pattern_intelligence_repository.save_patterns(run, patterns, {})
        return run

    def count(self):
        conn = weekly_priority_repository.get_connection()
        value = conn.execute("SELECT COUNT(*) FROM weekly_priorities").fetchone()[0]
        conn.close()
        return value

    def test_generation_is_automatic_ready_idempotent_and_explainable(self):
        first = self.pattern()
        duplicate_topic = self.pattern(
            title="Transizione difensiva da correggere",
            confidence=78,
            occurrence=0.66,
            source_prefix="second",
        )
        self.save_run([first, duplicate_topic])

        result = weekly_priority_service.sync_from_patterns(1)
        self.assertTrue(result["generated"])
        self.assertEqual(len(result["priorities"]), 1)
        priority = result["priorities"][0]
        self.assertEqual(priority["status"], "PROPOSED")
        self.assertEqual(len(priority["pattern_ids"]), 2)
        self.assertEqual(len(priority["canonical_match_ids"]), 3)
        self.assertEqual(set(priority["references"]["matches"]), {"match-1", "match-2", "match-3"})
        self.assertTrue(priority["references"]["voice_coach"])
        self.assertTrue(priority["references"]["video_ai"])
        self.assertTrue(priority["references"]["coach_notes"])
        self.assertEqual(priority["reason"]["code"], "CONSOLIDATED_PATTERN")
        self.assertIn("frequency", priority["reason"]["factors"])

        again = weekly_priority_service.sync_from_patterns(1)
        self.assertEqual(self.count(), 1)
        self.assertEqual(
            again["priorities"][0]["priority_id"],
            priority["priority_id"],
        )

    def test_ranking_is_deterministic_and_orders_stronger_priority_first(self):
        strong = self.pattern()
        weak = self.pattern(
            topic="width",
            title="Ampiezza offensiva",
            phase="possession",
            confidence=58,
            occurrence=0.34,
            matches=3,
            source_prefix="width",
        )
        self.save_run([weak, strong])
        first = weekly_priority_service.sync_from_patterns(1)["priorities"]
        second = weekly_priority_service.sync_from_patterns(1)["priorities"]

        self.assertEqual(
            [item["priority_id"] for item in first],
            [item["priority_id"] for item in second],
        )
        self.assertGreater(first[0]["ranking_score"], first[1]["ranking_score"])
        self.assertEqual(first[0]["topic"], strong["title"])

    def test_non_consolidated_and_contradictory_patterns_are_excluded(self):
        candidate = self.pattern(status="monitoring")
        contradictory = self.pattern(
            topic="pressing",
            title="Pressing",
            phase="defending",
        )
        contradictory["contradictory"] = True
        self.save_run([candidate, contradictory])

        result = weekly_priority_service.sync_from_patterns(1)
        self.assertFalse(result["generated"])
        self.assertEqual(result["priorities"], [])
        self.assertEqual(self.count(), 0)

    def test_staff_confirm_dismiss_and_modify_preserve_evidence(self):
        self.save_run([self.pattern()])
        priority = weekly_priority_service.sync_from_patterns(1)["priorities"][0]
        original_evidence = list(priority["evidence_ids"])

        confirmed = weekly_priority_service.set_staff_status(
            1,
            priority["priority_id"],
            status="CONFIRMED",
            staff_reason="Confermato dallo staff",
            topic=None,
            phase=None,
            priority_level=None,
        )
        self.assertEqual(confirmed["status"], "CONFIRMED")
        self.assertEqual(confirmed["staff_status"], "CONFIRMED")
        self.assertEqual(confirmed["evidence_ids"], original_evidence)
        self.assertEqual(confirmed["staff_updated_by"], 1)
        self.assertIsNotNone(confirmed["staff_updated_at"])
        draft = training_planner_repository.latest_plan(1)
        self.assertIsNotNone(draft)
        self.assertEqual(
            draft["current_plan"]["sessions"][0]["priority_ids"],
            [priority["priority_id"]],
        )

        modified = weekly_priority_service.set_staff_status(
            1,
            priority["priority_id"],
            status="MODIFIED",
            staff_reason="Tema rinominato senza perdere le fonti",
            topic="Protezione preventiva",
            phase="rest_defense",
            priority_level="HIGH",
        )
        self.assertEqual(modified["topic"], "Protezione preventiva")
        self.assertEqual(modified["phase"], "rest_defense")
        self.assertEqual(modified["evidence_ids"], original_evidence)

        weekly_priority_service.sync_from_patterns(1)
        persisted = weekly_priority_service.detail(1, priority["priority_id"])
        self.assertEqual(persisted["topic"], "Protezione preventiva")
        self.assertEqual(persisted["status"], "MODIFIED")
        self.assertEqual(persisted["evidence_ids"], original_evidence)

        dismissed = weekly_priority_service.set_staff_status(
            1,
            priority["priority_id"],
            status="DISMISSED",
            staff_reason="Non prioritaria questa settimana",
            topic=None,
            phase=None,
            priority_level=None,
        )
        self.assertEqual(dismissed["status"], "DISMISSED")
        self.assertEqual(weekly_priority_service.list_current(1), [])
        self.assertEqual(
            len(
                weekly_priority_repository.list_latest(
                    1,
                    include_dismissed=True,
                )
            ),
            1,
        )

    def test_user_isolation(self):
        self.save_run([self.pattern()])
        priority = weekly_priority_service.sync_from_patterns(1)["priorities"][0]
        self.assertIsNone(
            weekly_priority_service.detail(2, priority["priority_id"])
        )
        self.assertIsNone(
            weekly_priority_service.set_staff_status(
                2,
                priority["priority_id"],
                status="CONFIRMED",
                staff_reason=None,
                topic=None,
                phase=None,
                priority_level=None,
            )
        )


if __name__ == "__main__":
    unittest.main()
