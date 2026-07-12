import sqlite3
import sys
import tempfile
import types
import unittest
from datetime import date,timedelta
from pathlib import Path

try:
    import psycopg2  # noqa: F401
except ModuleNotFoundError:
    pg=types.ModuleType("psycopg2"); extras=types.ModuleType("psycopg2.extras"); extras.RealDictCursor=object; pg.extras=extras
    sys.modules["psycopg2"]=pg; sys.modules["psycopg2.extras"]=extras

from app.models.pattern_intelligence import PatternRunRequest
from app.models.training_planner import TrainingPlanGenerateRequest
from app.repositories import knowledge_intelligence_repository,knowledge_intelligence_search_repository,knowledge_repository,pattern_intelligence_repository,training_planner_repository,voice_coach_repository,weekly_briefing_repository
from app.repositories import knowledge_intelligence_schema
from app.services import knowledge_intelligence_adapters,knowledge_intelligence_service,knowledge_intelligence_sync,knowledge_service,pattern_intelligence_aggregator,pattern_intelligence_service,training_planner_service,voice_coach_intelligence_service,weekly_briefing_service
from app.services.knowledge_intelligence_registry import validate_relation


class KnowledgeIntelligenceTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.db_path=Path(self.tmp.name)/"knowledge-intelligence.db"; self.originals=[]
        def connection():
            conn=sqlite3.connect(self.db_path); conn.row_factory=sqlite3.Row; conn.execute("PRAGMA foreign_keys=ON"); return conn
        modules=(knowledge_repository,voice_coach_repository,pattern_intelligence_repository,pattern_intelligence_aggregator,weekly_briefing_repository,training_planner_repository,knowledge_intelligence_schema,knowledge_intelligence_repository,knowledge_intelligence_search_repository,knowledge_intelligence_adapters)
        for module in modules:
            self.originals.append((module,module.get_connection,getattr(module,"USE_POSTGRES",None))); module.get_connection=connection
            if hasattr(module,"USE_POSTGRES"): module.USE_POSTGRES=False
        conn=connection(); conn.execute("CREATE TABLE users(id INTEGER PRIMARY KEY,email TEXT)"); conn.executemany("INSERT INTO users VALUES(?,?)",[(1,"one@test.it"),(2,"two@test.it")])
        conn.execute("CREATE TABLE saved_matches(id INTEGER PRIMARY KEY,user_id INTEGER,match_id INTEGER,home TEXT,away TEXT,league TEXT,created_at TEXT)")
        conn.execute("CREATE TABLE saved_players(id INTEGER PRIMARY KEY,user_id INTEGER,player_name TEXT,team TEXT,role TEXT,notes TEXT,created_at TEXT)")
        conn.execute("CREATE TABLE scout_reports(id INTEGER PRIMARY KEY,user_id INTEGER,match_id INTEGER,title TEXT,report_type TEXT,payload TEXT,created_at TEXT)")
        conn.execute("CREATE TABLE video_reports(id INTEGER PRIMARY KEY,user_id INTEGER,title TEXT,club_name TEXT,category TEXT,focus TEXT,observed_team TEXT,report_style TEXT,frames_analyzed INTEGER,report TEXT,pdf_base64 TEXT,payload TEXT,created_at TEXT)")
        conn.execute("CREATE TABLE video_assets(id INTEGER PRIMARY KEY,user_id INTEGER,title TEXT,club_name TEXT,category TEXT,source_type TEXT,source_url TEXT,file_path TEXT,file_name TEXT,mime_type TEXT,size_bytes INTEGER,rights_confirmed INTEGER,status TEXT,metadata TEXT,created_at TEXT,updated_at TEXT)")
        conn.execute("CREATE TABLE video_frame_feedback(id INTEGER PRIMARY KEY,user_id INTEGER,video_asset_id INTEGER,report_id INTEGER,frame_index INTEGER,frame_time REAL,source TEXT,status TEXT,requested_phase TEXT,detected_phase TEXT,corrected_phase TEXT,confidence REAL,notes TEXT,metadata TEXT,created_at TEXT)")
        conn.commit(); conn.close(); knowledge_service.initialize_foundation(); voice_coach_intelligence_service.initialize_voice_coach_intelligence(); pattern_intelligence_service.initialize_pattern_intelligence(); weekly_briefing_service.initialize_weekly_briefing(); training_planner_service.initialize_training_planner(); knowledge_intelligence_service.initialize_knowledge_intelligence()
        self.connection=connection; self.seed_sources()

    def tearDown(self):
        for module,connection,use_pg in self.originals:
            module.get_connection=connection
            if use_pg is not None: module.USE_POSTGRES=use_pg
        self.tmp.cleanup()

    def match(self,index):
        played=(date.today()-timedelta(days=index-1)).isoformat(); event={"id":f"e{index}","type":"palla_persa","minute":30,"zone":"central","note":"Palla persa centrale"}
        return {"id":f"m{index}","savedAt":played,"match":{"homeTeam":"MatchIQ","awayTeam":f"Rivale {index}","date":played,"category":"Dilettanti"},"events":[event],"ratings":[]}

    def seed_sources(self):
        workspace=knowledge_repository.get_or_create_workspace(1); wid=int(workspace["id"]); knowledge_repository.upsert_profile("knowledge_team_profiles",wid,{"category":"Dilettanti","notes":"Squadra intensa"},knowledge_repository.TEAM_COLUMNS); player=knowledge_repository.create_roster_player(wid,{"name":"Mario Rossi","role":"Centrocampista"})
        conn=self.connection(); now=date.today().isoformat(); conn.execute("INSERT INTO saved_matches VALUES(1,1,101,'MatchIQ','Rivale','Promozione',?)",(now,)); conn.execute("INSERT INTO video_assets VALUES(1,1,'Partita 1','MatchIQ','Dilettanti','upload',NULL,NULL,'match.mp4','video/mp4',1000,1,'ready',?, ?, ?)",('{"match_id":101}',now,now)); conn.execute("INSERT INTO video_reports VALUES(1,1,'Report partita','MatchIQ','Dilettanti','transizione negativa','MatchIQ','staff',4,'Sintesi',NULL,?,?)",('{"video_asset_id":1,"match_id":101}',now)); conn.execute("INSERT INTO video_frame_feedback VALUES(1,1,1,1,2,35.0,'ai','confirmed','transizione','negative_transition',NULL,0.8,'Frame utile','{}',?)",(now,)); conn.execute("INSERT INTO scout_reports VALUES(1,1,101,'Rossi','player',?,?)",(f'{{"player_id":"{player["id"]}","player_name":"Mario Rossi","summary":"Profilo osservato"}}',now)); conn.commit(); conn.close()
        voice_coach_repository.upsert_observation(1,wid,{"client_id":"voice-1","match_key":"101","match_id":"101","intent":"tactical_note","confidence":0.9,"original_text":"Rossi perde palla centralmente","normalized_summary":"Palla persa centrale","minute":30,"match_phase":"first_half","team":"ours","player_ids":[str(player["id"])],"player_names":["Mario Rossi"],"tactical_topic":"lost_ball","topic_label":"Transizione negativa","zone":"central","polarity":"negative","priority":"high","source":"voice","requires_confirmation":False,"ambiguities":[],"warnings":[],"evidence":[],"explanation":"Nota staff","status":"confirmed","metadata":{}}); voice_coach_repository.rebuild_themes(1,wid,"101")
        pattern_intelligence_service.run(1,PatternRunRequest(local_matches=[self.match(i) for i in range(1,4)]))
        weekly_briefing_repository.save_week(1,wid,date.today().isoformat(),"weekly-fp",{"patterns":1},{"title":"Briefing MatchIQ","summary":"Lavorare sulla transizione negativa"},[{"title":"Palla persa","topic":"negative_transition","reason":"Pattern ricorrente"}])
        training_planner_service.generate(1,TrainingPlanGenerateRequest(training_days=["Martedi","Giovedi"],players=18,goalkeepers=2,session_duration=90,intensity="media",category="Dilettanti",local_context={}))

    def test_initial_sync_indexes_real_sources_and_relations(self):
        result=knowledge_intelligence_service.sync(1,force=True); self.assertFalse(result["partial"])
        status=knowledge_intelligence_service.status(1); types=status["summary"]["by_type"]
        for required in ("match","voice_observation","voice_match_theme","historical_pattern","weekly_briefing","training_plan","training_session","training_exercise","video_session","video_frame","video_report","player","scout_report"): self.assertGreater(types.get(required,0),0,required)
        self.assertGreater(status["summary"]["edges"],0)

    def test_sync_is_idempotent_and_retry_does_not_duplicate(self):
        first=knowledge_intelligence_service.sync(1,force=True); before=knowledge_intelligence_service.status(1)["summary"]
        second=knowledge_intelligence_service.sync(1); after=knowledge_intelligence_service.status(1)["summary"]
        self.assertEqual(before["nodes"],after["nodes"]); self.assertEqual(before["edges"],after["edges"]); self.assertTrue(all(item["status"]=="unchanged" for item in second["modules"].values()))

    def test_significant_change_versions_but_read_timestamp_does_not(self):
        knowledge_intelligence_service.sync(1,force=True); result=knowledge_intelligence_service.search(1,{"node_type":"voice_observation","page":1,"page_size":20}); node=result["items"][0]; versions=len(knowledge_intelligence_service.detail(1,node["id"])["versions"])
        knowledge_intelligence_service.sync(1,modules=["voice_coach"],force=True); self.assertEqual(len(knowledge_intelligence_service.detail(1,node["id"])["versions"]),versions)
        conn=self.connection(); conn.execute("UPDATE voice_coach_observations SET normalized_summary='Palla persa grave' WHERE user_id=1 AND client_id='voice-1'"); conn.commit(); conn.close(); knowledge_intelligence_service.sync(1,modules=["voice_coach"]); self.assertEqual(len(knowledge_intelligence_service.detail(1,node["id"])["versions"]),versions+1)

    def test_deleted_source_is_invalidated_without_losing_versions(self):
        knowledge_intelligence_service.sync(1,force=True); node=knowledge_intelligence_service.search(1,{"node_type":"voice_observation","page":1,"page_size":20})["items"][0]; conn=self.connection(); conn.execute("DELETE FROM voice_coach_observations WHERE user_id=1"); conn.commit(); conn.close(); knowledge_intelligence_service.sync(1,modules=["voice_coach"],force=True); detail=knowledge_intelligence_service.detail(1,node["id"]); self.assertFalse(detail["node"]["is_active"]); self.assertEqual(detail["node"]["validation_state"],"source_removed"); self.assertGreaterEqual(len(detail["versions"]),2)

    def test_search_timeline_pagination_validation_notes_and_ownership(self):
        knowledge_intelligence_service.sync(1,force=True); search=knowledge_intelligence_service.search(1,{"text":"Rossi","page":1,"page_size":2}); self.assertGreater(search["total"],0); self.assertLessEqual(len(search["items"]),2); node=search["items"][0]
        timeline=knowledge_intelligence_service.timeline(1,{"page":1,"page_size":3}); self.assertGreater(timeline["total"],0); self.assertLessEqual(len(timeline["items"]),3)
        validated=knowledge_intelligence_service.validate(1,node["id"],"confirmed_by_staff","Verificato"); self.assertEqual(validated["validation_state"],"confirmed_by_staff"); self.assertTrue(knowledge_intelligence_service.detail(1,node["id"])["notes"])
        self.assertIsNone(knowledge_intelligence_service.detail(2,node["id"])); self.assertEqual(knowledge_intelligence_service.search(2,{"text":"Rossi","page":1,"page_size":20})["total"],0)

    def test_relation_taxonomy_and_future_memory_contract(self):
        with self.assertRaises(ValueError): validate_relation("training_plan","confirms")
        knowledge_intelligence_service.sync(1,force=True); result=knowledge_intelligence_service.memory_query(1,{"team":None,"question":{"text":"transizione"},"period":{},"themes":[],"players":[],"zones":[],"source_types":[],"minimum_reliability":"bassa","limit":10}); self.assertIn("query_applied",result); self.assertIn("provenance",result); self.assertIn("contradictions",result); self.assertTrue(result["limits"])

    def test_module_failure_is_partial_and_preserves_other_sources(self):
        original=knowledge_intelligence_adapters.ADAPTERS["scout"]; knowledge_intelligence_adapters.ADAPTERS["scout"]=lambda *_: (_ for _ in ()).throw(RuntimeError("offline"))
        try:
            result=knowledge_intelligence_service.sync(1,force=True); self.assertTrue(result["partial"]); self.assertEqual(result["modules"]["scout"]["status"],"error"); self.assertEqual(result["modules"]["knowledge"]["status"],"completed")
        finally: knowledge_intelligence_adapters.ADAPTERS["scout"]=original


if __name__=="__main__": unittest.main()
