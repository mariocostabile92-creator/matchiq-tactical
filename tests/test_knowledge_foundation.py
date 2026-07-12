import sqlite3
import sys
import tempfile
import types
import unittest
from pathlib import Path

try:
    import psycopg2  # noqa: F401
except ModuleNotFoundError:
    psycopg2_stub = types.ModuleType("psycopg2")
    psycopg2_extras_stub = types.ModuleType("psycopg2.extras")
    psycopg2_extras_stub.RealDictCursor = object
    psycopg2_stub.extras = psycopg2_extras_stub
    sys.modules["psycopg2"] = psycopg2_stub
    sys.modules["psycopg2.extras"] = psycopg2_extras_stub

from app.models.knowledge import CoachProfileUpdate, RosterPlayerCreate, RosterPlayerUpdate, TeamProfileUpdate
from app.repositories import knowledge_repository as repository
from app.services import knowledge_service


class KnowledgeFoundationTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "knowledge.db"
        self.original_get_connection = repository.get_connection
        self.original_use_postgres = repository.USE_POSTGRES

        def connection():
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            return conn

        repository.get_connection = connection
        repository.USE_POSTGRES = False
        conn = connection()
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT NOT NULL)")
        conn.execute("INSERT INTO users (id, email) VALUES (1, 'staff@matchiq.test')")
        conn.commit()
        conn.close()
        knowledge_service.initialize_foundation()

    def tearDown(self):
        repository.get_connection = self.original_get_connection
        repository.USE_POSTGRES = self.original_use_postgres
        self.temp_dir.cleanup()

    def test_foundation_persists_profiles_and_roster(self):
        initial = knowledge_service.get_knowledge(1)
        same_workspace = knowledge_service.get_knowledge(1)
        self.assertEqual(initial.id, same_workspace.id)
        self.assertEqual(initial.roster, [])
        self.assertEqual(initial.source_links, [])

        updated = knowledge_service.update_coach_profile(
            1,
            CoachProfileUpdate(
                coach_name="Mario Rossi",
                preferred_formation="4-3-3",
                tactical_principles=["Pressing orientato", "Ampiezza"],
            ),
        )
        self.assertEqual(updated.coach_profile.coach_name, "Mario Rossi")
        self.assertEqual(updated.coach_profile.tactical_principles, ["Pressing orientato", "Ampiezza"])

        updated = knowledge_service.update_team_profile(
            1,
            TeamProfileUpdate(
                category="Prima squadra",
                average_age=24.5,
                player_count=23,
                goalkeeper_count=3,
                strengths=["Transizioni"],
            ),
        )
        self.assertEqual(updated.team_profile.player_count, 23)
        self.assertEqual(updated.team_profile.strengths, ["Transizioni"])

        player = knowledge_service.add_roster_player(
            1,
            RosterPlayerCreate(
                name="Luca Bianchi",
                role="Centrocampista",
                preferred_foot="Destro",
                characteristics=["Visione di gioco"],
                technique=78,
                secondary_roles=["Trequartista"],
            ),
        )
        self.assertEqual(player["technique"], 78)

        player = knowledge_service.replace_roster_player(
            1,
            player["id"],
            RosterPlayerUpdate(
                name="Luca Bianchi",
                role="Regista",
                characteristics=["Visione di gioco", "Cambio campo"],
                technique=82,
            ),
        )
        self.assertEqual(player["role"], "Regista")
        self.assertEqual(player["technique"], 82)

        reloaded = knowledge_service.get_knowledge(1)
        self.assertEqual(len(reloaded.roster), 1)
        self.assertEqual(reloaded.roster[0].secondary_roles, [])
        self.assertTrue(knowledge_service.remove_roster_player(1, player["id"]))
        self.assertEqual(knowledge_service.get_knowledge(1).roster, [])

    def test_user_data_is_isolated(self):
        conn = repository.get_connection()
        conn.execute("INSERT INTO users (id, email) VALUES (2, 'other@matchiq.test')")
        conn.commit()
        conn.close()
        knowledge_service.update_coach_profile(1, CoachProfileUpdate(coach_name="Staff Uno"))
        knowledge_service.update_coach_profile(2, CoachProfileUpdate(coach_name="Staff Due"))
        self.assertEqual(knowledge_service.get_knowledge(1).coach_profile.coach_name, "Staff Uno")
        self.assertEqual(knowledge_service.get_knowledge(2).coach_profile.coach_name, "Staff Due")


if __name__ == "__main__":
    unittest.main()
