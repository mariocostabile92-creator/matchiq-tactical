import sqlite3
import sys
import tempfile
import types
import unittest
from datetime import date, timedelta
from pathlib import Path

try:
    import psycopg2  # noqa: F401
except ModuleNotFoundError:
    pg=types.ModuleType("psycopg2")
    extras=types.ModuleType("psycopg2.extras")
    extras.RealDictCursor=object
    pg.extras=extras
    sys.modules["psycopg2"]=pg
    sys.modules["psycopg2.extras"]=extras

from app.models.pattern_intelligence import PatternRunRequest
from app.models.training_planner import TrainingPlanGenerateRequest
from app.repositories import (
    knowledge_repository,
    pattern_intelligence_repository,
    training_planner_repository,
    voice_coach_repository,
    weekly_briefing_repository,
)
from app.services import (
    knowledge_service,
    pattern_intelligence_aggregator,
    pattern_intelligence_service,
    training_planner_service,
    voice_coach_intelligence_service,
    weekly_briefing_service,
)


class TrainingPlannerTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db_path=Path(self.tmp.name)/"training.db"
        self.originals=[]

        def connection():
            conn=sqlite3.connect(self.db_path)
            conn.row_factory=sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            return conn

        modules=(
            knowledge_repository,
            voice_coach_repository,
            pattern_intelligence_repository,
            pattern_intelligence_aggregator,
            weekly_briefing_repository,
            training_planner_repository,
        )
        for module in modules:
            self.originals.append((module,module.get_connection,getattr(module,"USE_POSTGRES",None)))
            module.get_connection=connection
            if hasattr(module,"USE_POSTGRES"):
                module.USE_POSTGRES=False

        conn=connection()
        conn.execute("CREATE TABLE users(id INTEGER PRIMARY KEY,email TEXT)")
        conn.executemany("INSERT INTO users VALUES(?,?)",[(1,"one@test.it"),(2,"two@test.it")])
        conn.execute("CREATE TABLE saved_matches(id INTEGER PRIMARY KEY,user_id INTEGER,match_id INTEGER,home TEXT,away TEXT,league TEXT,created_at TEXT)")
        conn.execute("CREATE TABLE video_reports(id INTEGER PRIMARY KEY,user_id INTEGER,title TEXT,focus TEXT,observed_team TEXT,frames_analyzed INTEGER,created_at TEXT)")
        conn.execute("CREATE TABLE video_frame_feedback(id INTEGER PRIMARY KEY,user_id INTEGER,video_asset_id INTEGER,report_id INTEGER,frame_index INTEGER,frame_time REAL,status TEXT,requested_phase TEXT,detected_phase TEXT,corrected_phase TEXT,confidence REAL,notes TEXT,created_at TEXT)")
        conn.commit()
        conn.close()
        knowledge_service.initialize_foundation()
        voice_coach_intelligence_service.initialize_voice_coach_intelligence()
        pattern_intelligence_service.initialize_pattern_intelligence()
        weekly_briefing_service.initialize_weekly_briefing()
        training_planner_service.initialize_training_planner()

    def tearDown(self):
        for module,connection,use_pg in self.originals:
            module.get_connection=connection
            if use_pg is not None:
                module.USE_POSTGRES=use_pg
        self.tmp.cleanup()

    def match(self,index):
        played=(date.today()-timedelta(days=index-1)).isoformat()
        event={"id":f"lost-{index}","type":"palla_persa","minute":30,"zone":"central","note":"Palla persa centrale"}
        return {"id":f"m{index}","savedAt":played,"match":{"homeTeam":"MatchIQ","awayTeam":f"Rivale {index}","date":played,"category":"Dilettanti"},"events":[event],"ratings":[]}

    def request(self,force=False):
        return TrainingPlanGenerateRequest(
            training_days=["Martedi","Giovedi"],
            players=18,
            goalkeepers=2,
            session_duration=90,
            intensity="media",
            category="Dilettanti",
            local_context={},
            force=force,
        )

    def establish_pattern(self):
        matches=[self.match(index) for index in range(1,4)]
        result=pattern_intelligence_service.run(1,PatternRunRequest(local_matches=matches))
        self.assertEqual(result["data"]["items"][0]["status"],"established")

    def test_library_is_curated_and_complete(self):
        items=training_planner_repository.list_exercises(limit=50)
        self.assertGreaterEqual(len(items),10)
        self.assertLessEqual(len(items),20)
        required={"objective","description","min_players","max_players","goalkeepers","field_dimensions","duration","materials","intensity","difficulty","progression","regression","coach_corrections","source","reliability_level","validation_status","version"}
        self.assertTrue(all(required.issubset(item) for item in items))

    def test_refuses_generic_plan_when_sources_are_insufficient(self):
        result=training_planner_service.generate(1,self.request())
        self.assertFalse(result["data"]["sufficient"])
        self.assertIsNone(result["data"]["plan"])
        self.assertIn("dati sufficienti",result["data"]["message"])

    def test_builds_a_motivated_week_from_real_priorities(self):
        self.establish_pattern()
        result=training_planner_service.generate(1,self.request())
        plan=result["data"]["plan"]
        self.assertTrue(result["generated"])
        self.assertLessEqual(len(plan["priorities"]),3)
        self.assertEqual(plan["training_days"],["Martedi","Giovedi"])
        self.assertEqual([item["day"] for item in plan["current_plan"]["sessions"]],["Martedi","Giovedi"])
        self.assertTrue(all(len(item["drills"])<=2 for item in plan["current_plan"]["sessions"]))
        self.assertTrue(plan["sources"])
        self.assertTrue(all(priority["reason"] and priority["sources"] for priority in plan["priorities"]))

    def test_idempotence_regeneration_and_history(self):
        self.establish_pattern()
        first=training_planner_service.generate(1,self.request())
        same=training_planner_service.generate(1,self.request())
        self.assertFalse(same["generated"])
        self.assertEqual(first["data"]["plan"]["id"],same["data"]["plan"]["id"])
        regenerated=training_planner_service.generate(1,self.request(force=True))
        self.assertNotEqual(first["data"]["plan"]["id"],regenerated["data"]["plan"]["id"])
        old=training_planner_repository.get_plan(1,first["data"]["plan"]["id"])
        self.assertEqual(old["status"],"archiviata")
        self.assertGreaterEqual(len(training_planner_repository.history(1,old["id"])),2)

    def test_edit_preserves_original_and_actions_are_persistent(self):
        self.establish_pattern()
        plan=training_planner_service.generate(1,self.request())["data"]["plan"]
        original=plan["original_plan"]
        edited=dict(plan["current_plan"])
        edited["title"]="Settimana adattata dallo staff"
        modified=training_planner_service.modify(1,plan["id"],edited,"Carico ridotto")
        self.assertEqual(modified["status"],"modificata")
        self.assertEqual(modified["original_plan"],original)
        self.assertEqual(modified["current_plan"]["title"],"Settimana adattata dallo staff")
        self.assertEqual(modified["version"],2)
        accepted=training_planner_service.action(1,plan["id"],"accept","Confermato")
        self.assertEqual(accepted["status"],"accettata")
        duplicated=training_planner_service.action(1,plan["id"],"duplicate",None)
        self.assertEqual(duplicated["status"],"bozza")
        self.assertNotEqual(duplicated["id"],plan["id"])

    def test_ownership_and_knowledge_links(self):
        self.establish_pattern()
        plan=training_planner_service.generate(1,self.request())["data"]["plan"]
        self.assertIsNone(training_planner_service.get(2,plan["id"]))
        self.assertIsNone(training_planner_service.modify(2,plan["id"],plan["current_plan"],None))
        workspace=knowledge_repository.get_or_create_workspace(1)
        links=knowledge_repository.list_source_links(workspace["id"])
        self.assertTrue(any(item["source_type"]=="training_plan" for item in links))


if __name__=="__main__":
    unittest.main()
