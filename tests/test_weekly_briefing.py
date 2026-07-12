import sqlite3
import sys
import tempfile
import types
import unittest
from datetime import date
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

from app.models.weekly_briefing import WeeklyBriefingGenerateRequest
from app.repositories import knowledge_repository, voice_coach_repository, weekly_briefing_repository
from app.services import knowledge_service, voice_coach_intelligence_service, weekly_briefing_service


class WeeklyBriefingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "weekly.db"
        self.originals = []

        def connection():
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            return conn

        for repository in (knowledge_repository, voice_coach_repository, weekly_briefing_repository):
            self.originals.append((repository, repository.get_connection, repository.USE_POSTGRES))
            repository.get_connection = connection
            repository.USE_POSTGRES = False
        conn = connection()
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT NOT NULL)")
        conn.executemany("INSERT INTO users (id, email) VALUES (?, ?)", [(1, "one@test.it"), (2, "two@test.it")])
        conn.execute("CREATE TABLE video_reports (id INTEGER PRIMARY KEY, user_id INTEGER, title TEXT, club_name TEXT, focus TEXT, frames_analyzed INTEGER, created_at TEXT)")
        conn.execute("CREATE TABLE video_assets (id INTEGER PRIMARY KEY, user_id INTEGER, title TEXT, status TEXT, created_at TEXT, updated_at TEXT)")
        conn.execute("CREATE TABLE saved_matches (id INTEGER PRIMARY KEY, user_id INTEGER, home TEXT, away TEXT, league TEXT, created_at TEXT)")
        conn.execute("CREATE TABLE video_frame_feedback (id INTEGER PRIMARY KEY, user_id INTEGER, created_at TEXT)")
        conn.commit(); conn.close()
        knowledge_service.initialize_foundation()
        voice_coach_intelligence_service.initialize_voice_coach_intelligence()
        weekly_briefing_service.initialize_weekly_briefing()

    def tearDown(self):
        for repository, get_connection, use_postgres in self.originals:
            repository.get_connection = get_connection
            repository.USE_POSTGRES = use_postgres
        self.tmp.cleanup()

    def _request(self, report="", lost=0):
        events = [{"type":"palla_persa", "tags":["transizione negativa"]} for _ in range(lost)]
        return WeeklyBriefingGenerateRequest(local_sources={
            "latest_match": {
                "savedAt": f"{date.today().isoformat()}T12:00:00+00:00",
                "match":{"homeTeam":"MatchIQ", "awayTeam":"Rivali", "date":date.today().isoformat(), "category":"Prima Categoria"},
                "homeGoals":2, "awayGoals":1, "events":events,
                "ratings":[{"player":"Rossi", "vote":7}, {"player":"Bianchi", "vote":6.5}], "report":report,
            },
            "history_count":1,
            "patterns":[{"label":"transizione negativa", "count":2, "source":"Coach"}],
            "captured_at":"stable",
        })

    def test_briefing_without_data_is_honest(self):
        result = weekly_briefing_service.generate(1, WeeklyBriefingGenerateRequest())
        content = result["briefing"]["content"]
        self.assertFalse(content["general"]["available"])
        self.assertEqual(content["went_well"], [])
        self.assertEqual(content["priorities"], [])
        malformed = weekly_briefing_service.build_briefing({"local":{"latest_match":[], "patterns":"invalid"}, "cloud":{}})
        self.assertFalse(malformed["general"]["available"])

    def test_persistence_read_state_and_no_regeneration_without_changes(self):
        first = weekly_briefing_service.generate(1, self._request(lost=2))
        same = self._request(lost=2)
        same.local_sources["captured_at"] = "different-but-not-new-data"
        second = weekly_briefing_service.generate(1, same)
        self.assertTrue(first["generated"])
        self.assertFalse(second["generated"])
        self.assertEqual(first["briefing"]["id"], second["briefing"]["id"])
        read = weekly_briefing_repository.mark_read(1, first["briefing"]["id"])
        self.assertTrue(read["is_read"])
        changed = weekly_briefing_service.generate(1, self._request(report="Report pronto", lost=2))
        self.assertTrue(changed["changed"])
        self.assertFalse(changed["briefing"]["is_read"])

    def test_sources_priorities_materials_and_ownership(self):
        week = weekly_briefing_service.current_week_key()
        conn = weekly_briefing_repository.get_connection()
        conn.execute("INSERT INTO video_assets (id,user_id,title,status,created_at,updated_at) VALUES (1,1,'Seduta','ready',?,?)", (week, week))
        conn.execute("INSERT INTO video_frame_feedback (id,user_id,created_at) VALUES (1,1,?)", (week,))
        conn.commit(); conn.close()
        result = weekly_briefing_service.generate(1, self._request(lost=3))
        content = result["briefing"]["content"]
        self.assertTrue(content["priorities"])
        self.assertEqual(content["materials"]["video_sessions"], 1)
        self.assertEqual(content["materials"]["frames"], 1)
        self.assertIsNone(weekly_briefing_repository.get_latest(2))
        self.assertIsNone(weekly_briefing_repository.mark_read(2, result["briefing"]["id"]))


if __name__ == "__main__":
    unittest.main()
