import os
import sqlite3
import tempfile
import unittest

from app.repositories import club_intelligence_repository as repository
from app.repositories import club_intelligence_schema as schema
from app.services import club_intelligence_service as service


class ClubIntelligenceTests(unittest.TestCase):
    def setUp(self):
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.path = handle.name; handle.close()

        def connection():
            conn = sqlite3.connect(self.path); conn.row_factory = sqlite3.Row; conn.execute("PRAGMA foreign_keys=ON"); return conn

        self.original_repo_connection = repository.get_connection
        self.original_schema_connection = schema.get_connection
        repository.get_connection = connection; schema.get_connection = connection
        conn = connection(); conn.executescript("""
            CREATE TABLE users(id INTEGER PRIMARY KEY,email TEXT);
            CREATE TABLE knowledge_workspaces(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL);
            CREATE TABLE knowledge_team_profiles(id INTEGER PRIMARY KEY,knowledge_id INTEGER,formations_used TEXT,playing_principles TEXT,category TEXT);
            CREATE TABLE knowledge_coach_profiles(id INTEGER PRIMARY KEY,knowledge_id INTEGER,preferred_formation TEXT,tactical_principles TEXT);
            CREATE TABLE tactical_identity_profiles(id INTEGER PRIMARY KEY,workspace_id INTEGER,created_at TEXT);
        """);
        conn.executemany("INSERT INTO users(id,email) VALUES(?,?)", [(1,"owner@test.it"),(2,"coach@test.it"),(3,"other@test.it")]); conn.commit(); conn.close()
        schema.initialize_schema()

    def tearDown(self):
        repository.get_connection = self.original_repo_connection; schema.get_connection = self.original_schema_connection
        try: os.unlink(self.path)
        except OSError: pass

    def test_club_creation_persists_owner_membership(self):
        club = service.create(1, {"name":"ASD MatchIQ","season":"2026/27","technical_principles":["Pressing coordinato"]})
        membership = repository.get_membership(club["id"], 1)
        self.assertEqual(membership["role"], "club_owner")
        self.assertTrue(membership["permissions_json"]["manage_club"])

    def test_team_visibility_isolated_by_assignment(self):
        club = service.create(1, {"name":"ASD MatchIQ"})
        first = service.add_team(club["id"], 1, {"name":"Prima squadra","team_type":"first_team","sharing_scope":"private","level_order":1})
        youth = service.add_team(club["id"], 1, {"name":"Juniores","team_type":"youth","sharing_scope":"private","level_order":2})
        repository.upsert_membership(club["id"], 2, "head_coach", [youth["id"]], {}, 1)
        visible = service.teams(club["id"], 2)
        self.assertEqual([item["id"] for item in visible], [youth["id"]])
        self.assertNotIn(first["id"], [item["id"] for item in visible])

    def test_workspace_requires_club_membership(self):
        club = service.create(1, {"name":"ASD MatchIQ"})
        conn = repository.get_connection(); conn.executemany("INSERT INTO knowledge_workspaces(id,user_id) VALUES(?,?)", [(10,2),(11,3)]); conn.commit(); conn.close()
        repository.upsert_membership(club["id"], 2, "head_coach", [], {}, 1)
        team = service.add_team(club["id"], 1, {"name":"Allievi","knowledge_workspace_id":10,"sharing_scope":"private"})
        self.assertEqual(team["workspace_owner_user_id"], 2)
        with self.assertRaises(ValueError): service.add_team(club["id"], 1, {"name":"Giovanissimi","knowledge_workspace_id":11,"sharing_scope":"private"})

    def test_comparison_is_contextual_and_never_ranks_teams(self):
        club = service.create(1, {"name":"ASD MatchIQ","technical_principles":["Aggressivita organizzata"]})
        one = service.add_team(club["id"], 1, {"name":"Prima squadra","category":"Eccellenza","sharing_scope":"private"})
        two = service.add_team(club["id"], 1, {"name":"Juniores","category":"U19","sharing_scope":"private"})
        result = service.overview(club["id"], 1, [one["id"], two["id"]])
        self.assertNotIn("ranking", result)
        self.assertNotIn("score", result)
        self.assertEqual(len(result["differences"]), 2)
        self.assertTrue(any("Categorie" in item for item in result["limitations"]))

    def test_non_director_cannot_compare_or_manage(self):
        club = service.create(1, {"name":"ASD MatchIQ"})
        team = service.add_team(club["id"], 1, {"name":"Allievi","sharing_scope":"private"})
        repository.upsert_membership(club["id"], 2, "assistant_coach", [team["id"]], {}, 1)
        result = service.overview(club["id"], 2)
        self.assertEqual(result["differences"], [])
        self.assertIn("notice", result["continuity"])
        with self.assertRaises(PermissionError): service.add_principle(club["id"], 2, {"title":"Pressing","principle_area":"pressing","description":"Pressione coordinata","source_kind":"declared_by_club","validation_state":"declared","team_ids":[]})

    def test_snapshot_keeps_sources_and_limitations(self):
        club = service.create(1, {"name":"ASD MatchIQ"})
        service.add_team(club["id"], 1, {"name":"Prima squadra","sharing_scope":"private"})
        snap = service.snapshot(club["id"], 1, [], "Luglio 2026")
        self.assertEqual(snap["period_label"], "Luglio 2026")
        self.assertTrue(snap["limitations_json"])
        self.assertIn("guardrails", snap["summary_json"])

    def test_team_principles_are_isolated_for_assigned_staff(self):
        club = service.create(1, {"name":"ASD MatchIQ"})
        first = service.add_team(club["id"], 1, {"name":"Prima squadra","sharing_scope":"private"})
        youth = service.add_team(club["id"], 1, {"name":"Juniores","sharing_scope":"private"})
        repository.upsert_membership(club["id"], 2, "head_coach", [youth["id"]], {}, 1)
        service.add_principle(club["id"], 1, {"title":"Club","principle_area":"general","description":"Principio comune","source_kind":"declared_by_club","validation_state":"declared","team_ids":[]})
        service.add_principle(club["id"], 1, {"title":"Prima","principle_area":"pressing","description":"Principio prima squadra","source_kind":"staff_validated","validation_state":"validated","team_ids":[first["id"]]})
        service.add_principle(club["id"], 1, {"title":"Juniores","principle_area":"build_up","description":"Principio Juniores","source_kind":"staff_validated","validation_state":"validated","team_ids":[youth["id"]]})
        self.assertEqual({item["title"] for item in service.principles(club["id"], 2)}, {"Club", "Juniores"})

    def test_owner_cannot_be_deactivated_or_demoted(self):
        club = service.create(1, {"name":"ASD MatchIQ"})
        owner = repository.get_membership(club["id"], 1)
        with self.assertRaises(ValueError):
            service.change_member(club["id"], owner["id"], 1, {"status":"inactive"})
        with self.assertRaises(ValueError):
            service.change_member(club["id"], owner["id"], 1, {"role":"viewer"})

    def test_member_assignments_must_belong_to_club(self):
        club = service.create(1, {"name":"ASD MatchIQ"})
        with self.assertRaises(ValueError):
            service.add_member(club["id"], 1, {"user_id":2,"role":"head_coach","team_ids":[999],"permissions":{}})

    def test_overview_rejects_hidden_team_selection(self):
        club = service.create(1, {"name":"ASD MatchIQ"})
        first = service.add_team(club["id"], 1, {"name":"Prima squadra","team_type":"first_team","sharing_scope":"private"})
        youth = service.add_team(club["id"], 1, {"name":"Juniores","team_type":"youth","sharing_scope":"private"})
        repository.upsert_membership(club["id"], 2, "head_coach", [youth["id"]], {}, 1)
        with self.assertRaises(PermissionError):
            service.overview(club["id"], 2, [first["id"]])

    def test_invalid_team_and_resource_scopes_are_rejected(self):
        club = service.create(1, {"name":"ASD MatchIQ"})
        with self.assertRaises(ValueError):
            service.add_team(club["id"], 1, {"name":"Squadra QA","team_type":"other","sharing_scope":"everyone"})
        with self.assertRaises(ValueError):
            service.add_principle(club["id"], 1, {"title":"Test","principle_area":"general","description":"Principio non valido","source_kind":"declared_by_club","validation_state":"automatic","team_ids":[]})


if __name__ == "__main__":
    unittest.main()
