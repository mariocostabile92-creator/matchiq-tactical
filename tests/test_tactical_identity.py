import sqlite3
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    import psycopg2  # noqa: F401
except ModuleNotFoundError:
    pg = types.ModuleType("psycopg2")
    extras = types.ModuleType("psycopg2.extras")
    extras.RealDictCursor = object
    pg.extras = extras
    sys.modules["psycopg2"] = pg
    sys.modules["psycopg2.extras"] = extras

from app.repositories import (
    knowledge_repository,
    tactical_identity_repository,
    tactical_identity_schema,
)
from app.services import knowledge_service, tactical_identity_service
from app.services.tactical_identity_engine import build
from app.services.tactical_identity_registry import DIMENSIONS, GROUPS
from app.services.tactical_identity_sources import _allowed, _matches_scope


class TacticalIdentityTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "identity.db"
        self.originals = []

        def connection():
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            return conn

        for module in (knowledge_repository, tactical_identity_schema, tactical_identity_repository):
            self.originals.append((module, module.get_connection, getattr(module, "USE_POSTGRES", None)))
            module.get_connection = connection
            if hasattr(module, "USE_POSTGRES"):
                module.USE_POSTGRES = False

        conn = connection()
        conn.execute("CREATE TABLE users(id INTEGER PRIMARY KEY,email TEXT,plan TEXT,is_active INTEGER)")
        conn.executemany(
            "INSERT INTO users VALUES(?,?,?,1)",
            [(1, "one@test.it", "pro"), (2, "two@test.it", "free")],
        )
        conn.commit()
        conn.close()
        knowledge_service.initialize_foundation()
        tactical_identity_service.initialize_tactical_identity()
        self.connection = connection
        self.workspace_one = knowledge_repository.get_or_create_workspace(1)
        self.workspace_two = knowledge_repository.get_or_create_workspace(2)

    def tearDown(self):
        for module, connection, use_postgres in self.originals:
            module.get_connection = connection
            if use_postgres is not None:
                module.USE_POSTGRES = use_postgres
        self.tmp.cleanup()

    @staticmethod
    def coach_node():
        return {
            "id": 1,
            "node_type": "coach_profile",
            "source_type": "knowledge_profile",
            "source_module": "knowledge",
            "source_id": "coach-1",
            "metadata_json": {
                "preferred_formation": "4-3-3",
                "alternative_formation": "4-2-3-1",
                "pressing": "pressione alta",
                "buildup": "costruzione corta",
            },
            "validation_state": "staff_source",
            "occurred_at": "2026-07-01T10:00:00",
            "updated_at": "2026-07-01T10:00:00",
        }

    @staticmethod
    def pressing_nodes(count=4):
        items = []
        for index in range(count):
            items.append(
                {
                    "id": index + 10,
                    "node_type": "coach_event",
                    "source_module": "coach",
                    "source_id": f"event-{index}",
                    "match_id": f"match-{index}",
                    "title": "Pressione alta coordinata",
                    "summary": "La squadra recupera palla alta con pressione coordinata.",
                    "tactical_topic": "pressing",
                    "reliability_level": "alta",
                    "validation_state": "confirmed_by_staff",
                    "nature": "osservazione_staff",
                    "polarity": "positive",
                    "occurred_at": f"2026-07-0{index + 2}T20:00:00",
                    "metadata_json": {"competition": "Campionato", "formation": "4-3-3"},
                }
            )
        return items

    def test_registry_covers_required_tactical_areas(self):
        self.assertEqual(
            set(GROUPS),
            {"structure", "buildup", "attack", "defence", "transitions", "set_pieces", "game_management", "squad"},
        )
        for dimension in (
            "structure.primary_formation",
            "buildup.third_man",
            "defence.high_press",
            "transition.counterpress",
            "set_piece.corner_defence",
            "game.change_reaction",
            "squad.characteristics",
        ):
            self.assertIn(dimension, DIMENSIONS)

    def test_postgres_schema_survives_duplicate_column_migrations(self):
        class TransactionalConnection:
            def __init__(self):
                self.pending_tables = False
                self.committed_tables = False
                self.indexes = 0

            def cursor(self):
                return self

            def execute(self, statement):
                normalized = " ".join(statement.split()).upper()
                if normalized.startswith("CREATE TABLE"):
                    self.pending_tables = True
                elif normalized.startswith("ALTER TABLE"):
                    raise RuntimeError("duplicate column")
                elif normalized.startswith("CREATE INDEX"):
                    if not self.committed_tables:
                        raise RuntimeError("undefined table")
                    self.indexes += 1

            def commit(self):
                if self.pending_tables:
                    self.committed_tables = True
                    self.pending_tables = False

            def rollback(self):
                self.pending_tables = False

            def close(self):
                return None

        connection = TransactionalConnection()
        with patch.object(tactical_identity_schema, "get_connection", return_value=connection), patch.object(
            tactical_identity_schema, "USE_POSTGRES", True
        ):
            tactical_identity_schema.initialize_schema()

        self.assertTrue(connection.committed_tables)
        self.assertEqual(connection.indexes, 8)

    def test_engine_separates_declared_observed_and_explains_limits(self):
        result = build([self.coach_node(), *self.pressing_nodes()])
        pressing = next(item for item in result["dimensions"] if item["dimension_type"] == "defence.high_press")
        formation = next(item for item in result["dimensions"] if item["dimension_type"] == "structure.primary_formation")
        self.assertEqual(formation["declared_value"], "4-3-3")
        self.assertIsNotNone(pressing["observed_value"])
        self.assertEqual(pressing["match_count"], 4)
        self.assertIn(pressing["alignment_state"], {"aligned", "evolving"})
        self.assertIn(pressing["confidence_level"], {"media", "alta"})
        self.assertTrue(pressing["explanation"])
        self.assertTrue(pressing["limitations"])
        self.assertEqual(len(pressing["evidence"]), 4)

    def test_repository_persists_versions_feedback_and_enforces_ownership(self):
        workspace_id = int(self.workspace_one["id"])
        scope = {"season": "2026/27", "competition": "Campionato", "formation": "4-3-3"}
        result = build([self.coach_node(), *self.pressing_nodes()])
        profile = tactical_identity_repository.save_profile(
            workspace_id,
            1,
            scope,
            {
                **result,
                "source_fingerprint": "fingerprint-1",
                "identity_version": 1,
            },
        )
        tactical_identity_repository.replace_dimensions(profile["id"], result["dimensions"])
        complete = tactical_identity_repository.full_profile(workspace_id, 1, profile)
        tactical_identity_repository.add_version(profile["id"], 1, complete, "Prima identita", "source_refresh", "user:1")
        pressing = next(item for item in complete["dimensions"] if item["dimension_type"] == "defence.high_press")
        confirmed = tactical_identity_repository.save_feedback(workspace_id, 1, pressing["id"], "confirmed", "Confermato dallo staff")
        self.assertEqual(confirmed["validation_state"], "confirmed_by_staff")
        self.assertEqual(confirmed["validated_value"], pressing["observed_value"])
        self.assertEqual(len(tactical_identity_repository.list_versions(profile["id"])), 1)
        self.assertIsNone(tactical_identity_repository.get_dimension(int(self.workspace_two["id"]), 2, pressing["id"]))
        self.assertIsNone(tactical_identity_repository.save_feedback(int(self.workspace_two["id"]), 2, pressing["id"], "contested"))

    def test_service_is_idempotent_and_versions_only_meaningful_changes(self):
        first_bundle = {
            "nodes": [self.coach_node(), *self.pressing_nodes()],
            "matches": 4,
            "sources": 5,
            "source_fingerprint": "fp-1",
        }
        same_identity_bundle = {**first_bundle, "source_fingerprint": "fp-2"}
        changed_bundle = {
            "nodes": [self.coach_node(), *self.pressing_nodes(5)],
            "matches": 5,
            "sources": 6,
            "source_fingerprint": "fp-3",
        }
        with patch.object(tactical_identity_service, "collect", return_value=first_bundle), patch.object(
            tactical_identity_service.tactical_identity_knowledge, "publish"
        ):
            first = tactical_identity_service.run(1, {"season": "2026/27"})
        self.assertTrue(first["generated"])
        self.assertEqual(first["data"]["identity_version"], 1)

        with patch.object(tactical_identity_service, "collect", return_value=first_bundle), patch.object(
            tactical_identity_service.tactical_identity_knowledge, "publish"
        ):
            unchanged = tactical_identity_service.run(1, {"season": "2026/27"})
        self.assertTrue(unchanged["unchanged"])
        self.assertEqual(unchanged["data"]["identity_version"], 1)

        with patch.object(tactical_identity_service, "collect", return_value=same_identity_bundle), patch.object(
            tactical_identity_service.tactical_identity_knowledge, "publish"
        ):
            refreshed = tactical_identity_service.run(1, {"season": "2026/27"})
        self.assertTrue(refreshed["evidence_refreshed"])
        self.assertEqual(refreshed["data"]["identity_version"], 1)

        with patch.object(tactical_identity_service, "collect", return_value=changed_bundle), patch.object(
            tactical_identity_service.tactical_identity_knowledge, "publish"
        ):
            changed = tactical_identity_service.run(1, {"season": "2026/27"})
        self.assertTrue(changed["generated"])
        self.assertEqual(changed["data"]["identity_version"], 2)
        self.assertEqual(len(changed["data"]["versions"]), 2)

    def test_processing_lock_blocks_parallel_runs_and_recovers_when_stale(self):
        workspace_id = int(self.workspace_one["id"])
        scope = {"season": "2026/27"}
        self.assertTrue(tactical_identity_repository.acquire_lock(workspace_id, 1, scope, "first"))
        self.assertFalse(tactical_identity_repository.acquire_lock(workspace_id, 1, scope, "parallel"))

        conn = self.connection()
        conn.execute(
            "UPDATE tactical_identity_profiles SET locked_at=? WHERE workspace_id=? AND user_id=?",
            ("2020-01-01T00:00:00+00:00", workspace_id, 1),
        )
        conn.commit()
        conn.close()

        self.assertTrue(tactical_identity_repository.acquire_lock(workspace_id, 1, scope, "retry"))
        recovered = tactical_identity_repository.get_profile(workspace_id, 1, scope)
        self.assertEqual(recovered["lock_token"], "retry")

    def test_source_quality_and_scope_filters_exclude_weak_inputs(self):
        weak_pattern = {"node_type": "historical_pattern", "validation_state": "candidate", "reliability_level": "bassa"}
        valid_pattern = {"node_type": "historical_pattern", "validation_state": "confirmed_by_staff", "reliability_level": "media"}
        orphan_video = {"node_type": "video_frame", "match_id": None, "validation_state": "confirmed", "reliability_level": "alta"}
        valid_video = {"node_type": "video_frame", "match_id": "m1", "validation_state": "accepted", "reliability_level": "media"}
        draft_training = {"node_type": "training_plan", "validation_state": "draft"}
        self.assertFalse(_allowed(weak_pattern))
        self.assertTrue(_allowed(valid_pattern))
        self.assertFalse(_allowed(orphan_video))
        self.assertTrue(_allowed(valid_video))
        self.assertFalse(_allowed(draft_training))
        scoped = {
            "metadata_json": {"competition": "Campionato Regionale", "formation": "4-3-3"},
            "search_text": "pressione alta",
        }
        self.assertTrue(_matches_scope(scoped, {"competition": "regionale", "formation": "4-3-3"}))
        self.assertFalse(_matches_scope(scoped, {"competition": "coppa"}))


if __name__ == "__main__":
    unittest.main()
