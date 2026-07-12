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
    pg=types.ModuleType("psycopg2"); extras=types.ModuleType("psycopg2.extras"); extras.RealDictCursor=object; pg.extras=extras
    sys.modules["psycopg2"]=pg; sys.modules["psycopg2.extras"]=extras

from app.models.pattern_intelligence import PatternRunRequest
from app.repositories import knowledge_repository, pattern_intelligence_repository, voice_coach_repository
from app.services import knowledge_service, pattern_intelligence_aggregator, pattern_intelligence_service, voice_coach_intelligence_service
from app.services.pattern_intelligence_confidence import confidence, trend
from app.services.pattern_intelligence_normalizer import normalize_event


class PatternIntelligenceTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.db_path=Path(self.tmp.name)/"patterns.db"; self.originals=[]
        def connection():
            conn=sqlite3.connect(self.db_path); conn.row_factory=sqlite3.Row; conn.execute("PRAGMA foreign_keys=ON"); return conn
        for module in (knowledge_repository,voice_coach_repository,pattern_intelligence_repository,pattern_intelligence_aggregator):
            self.originals.append((module,module.get_connection,getattr(module,"USE_POSTGRES",None)))
            module.get_connection=connection
            if hasattr(module,"USE_POSTGRES"): module.USE_POSTGRES=False
        conn=connection(); conn.execute("CREATE TABLE users(id INTEGER PRIMARY KEY,email TEXT)"); conn.executemany("INSERT INTO users VALUES(?,?)",[(1,"one@test.it"),(2,"two@test.it")])
        conn.execute("CREATE TABLE saved_matches(id INTEGER PRIMARY KEY,user_id INTEGER,match_id INTEGER,home TEXT,away TEXT,league TEXT,created_at TEXT)")
        conn.execute("CREATE TABLE video_reports(id INTEGER PRIMARY KEY,user_id INTEGER,title TEXT,focus TEXT,observed_team TEXT,frames_analyzed INTEGER,created_at TEXT)")
        conn.execute("CREATE TABLE video_frame_feedback(id INTEGER PRIMARY KEY,user_id INTEGER,video_asset_id INTEGER,report_id INTEGER,frame_index INTEGER,frame_time REAL,status TEXT,requested_phase TEXT,detected_phase TEXT,corrected_phase TEXT,confidence REAL,notes TEXT,created_at TEXT)")
        conn.commit(); conn.close(); knowledge_service.initialize_foundation(); voice_coach_intelligence_service.initialize_voice_coach_intelligence(); pattern_intelligence_service.initialize_pattern_intelligence()

    def tearDown(self):
        for module,connection,use_pg in self.originals:
            module.get_connection=connection
            if use_pg is not None: module.USE_POSTGRES=use_pg
        self.tmp.cleanup()

    def match(self,index,events,days_ago=0):
        played=(date.today()-timedelta(days=days_ago)).isoformat()
        return {"id":f"m{index}","savedAt":played,"match":{"homeTeam":"MatchIQ","awayTeam":f"Rivale {index}","date":played,"category":"Dilettanti"},"events":events,"ratings":[]}

    def lost(self,event_id,minute=30,note="Palla persa centrale"):
        return {"id":event_id,"type":"palla_persa","minute":minute,"zone":"central","note":note}

    def test_insufficient_samples_and_real_recurrence(self):
        empty=pattern_intelligence_service.run(1,PatternRunRequest(local_matches=[]))
        self.assertEqual(empty["data"]["items"],[])
        two=[self.match(1,[self.lost("e1"),self.lost("e2",31)]),self.match(2,[self.lost("e3")],1)]
        candidate=pattern_intelligence_service.run(1,PatternRunRequest(local_matches=two))
        self.assertEqual(candidate["data"]["items"][0]["status"],"candidate")
        three=two+[self.match(3,[self.lost("e4")],2)]
        established=pattern_intelligence_service.run(1,PatternRunRequest(local_matches=three))
        item=established["data"]["items"][0]
        self.assertEqual(item["status"],"established"); self.assertEqual(item["matches_count"],3); self.assertEqual(item["frequency_count"],4); self.assertEqual(item["matches_total"],3)

    def test_deduplication_and_context_separation(self):
        matches=[self.match(1,[self.lost("same"),self.lost("same")]),self.match(2,[self.lost("b")],1),self.match(3,[self.lost("c")],2)]
        result=pattern_intelligence_service.run(1,PatternRunRequest(local_matches=matches))
        self.assertEqual(result["data"]["items"][0]["frequency_count"],3)
        contexts=[self.match(4,[self.lost("d",10)]),self.match(5,[self.lost("e",75)],1),self.match(6,[self.lost("f",75)],2)]
        separated=pattern_intelligence_service.run(1,PatternRunRequest(local_matches=contexts,force=True))
        self.assertEqual(separated["data"]["items"],[])

    def test_semantic_normalization_reuses_voice_taxonomy(self):
        phrases=["secondo palo libero","uomo perso sul palo dietro","chiusura tardiva sul secondo palo"]
        topics={normalize_event({"type":"nota","note":text})["topic"] for text in phrases}
        self.assertEqual(topics,{"second_post"})
        corner=normalize_event({"type":"nota","note":"secondo palo su corner","phase":"set_piece"})
        open_play=normalize_event({"type":"nota","note":"secondo palo libero","phase":"second_half"})
        self.assertEqual(corner["topic"],open_play["topic"]); self.assertNotEqual(corner["phase"],open_play["phase"])

    def test_confidence_contradictions_and_trends(self):
        base=[{"objective_or_subjective":"staff_observation","polarity":"negative","match_id":"m1"},{"objective_or_subjective":"staff_observation","polarity":"negative","match_id":"m2"},{"objective_or_subjective":"objective","polarity":"positive","match_id":"m3"}]
        score=confidence(base,3,4); self.assertTrue(score["contradictory"]); self.assertLess(score["score"],72)
        growing=[{"match_id":"m3"},{"match_id":"m4"}]; self.assertEqual(trend(growing,["m1","m2","m3","m4"]),"in aumento")
        falling=[{"match_id":"m1"},{"match_id":"m2"}]; self.assertEqual(trend(falling,["m1","m2","m3","m4"]),"in diminuzione")
        stable=[{"match_id":x} for x in ["m1","m2","m3","m4"]]; self.assertEqual(trend(stable,["m1","m2","m3","m4"]),"stabile")
        self.assertEqual(trend([], ["m1","m2"]),"non determinabile")

    def test_idempotence_staff_state_notes_and_ownership(self):
        matches=[self.match(i,[self.lost(f"e{i}")],i-1) for i in range(1,4)]
        first=pattern_intelligence_service.run(1,PatternRunRequest(local_matches=matches)); pattern=first["data"]["items"][0]
        same=pattern_intelligence_service.run(1,PatternRunRequest(local_matches=matches)); self.assertFalse(same["generated"]); self.assertEqual(first["data"]["run"]["id"],same["data"]["run"]["id"])
        confirmed=pattern_intelligence_service.set_status(1,pattern["id"],"confirmed_by_staff"); self.assertEqual(confirmed["status"],"confirmed_by_staff")
        noted=pattern_intelligence_service.add_note(1,pattern["id"],"Verificare con lo staff"); self.assertEqual(noted["staff_note"],"Verificare con lo staff")
        self.assertIsNone(pattern_intelligence_service.detail(2,pattern["id"])); self.assertIsNone(pattern_intelligence_service.set_status(2,pattern["id"],"resolved"))

    def test_knowledge_links_without_profile_mutation(self):
        before=knowledge_repository.get_profile("knowledge_team_profiles",knowledge_repository.get_or_create_workspace(1)["id"],knowledge_repository.TEAM_COLUMNS)
        matches=[self.match(i,[self.lost(f"e{i}")],i-1) for i in range(1,4)]
        pattern_intelligence_service.run(1,PatternRunRequest(local_matches=matches))
        workspace=knowledge_repository.get_or_create_workspace(1); links=knowledge_repository.list_source_links(workspace["id"])
        self.assertTrue(any(item["source_type"]=="pattern_intelligence_run" for item in links)); self.assertTrue(any(item["source_type"]=="pattern_intelligence_pattern" for item in links))
        after=knowledge_repository.get_profile("knowledge_team_profiles",workspace["id"],knowledge_repository.TEAM_COLUMNS); self.assertEqual(before,after)

    def test_post_match_impact_is_non_blocking_and_evidence_based(self):
        matches=[self.match(i,[self.lost(f"e{i}")],i-1) for i in range(1,4)]; pattern_intelligence_service.run(1,PatternRunRequest(local_matches=matches))
        impact=pattern_intelligence_service.post_match_impact(1,{"events":[self.lost("new")]}); self.assertTrue(impact["strengthened"])
        neutral=pattern_intelligence_service.post_match_impact(2,{"events":[]}); self.assertEqual(neutral["strengthened"],[])


if __name__=="__main__": unittest.main()
