import sqlite3
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from app.models.match_evidence import MatchEvidenceFinalizeRequest
from app.repositories import (
    knowledge_intelligence_repository,
    knowledge_repository,
    match_evidence_repository,
    pattern_intelligence_repository,
    training_planner_repository,
    weekly_priority_repository,
)
from app.repositories import knowledge_intelligence_schema
from app.services import (
    knowledge_intelligence_adapters,
    knowledge_service,
    match_evidence_service,
    pattern_intelligence_aggregator,
    pattern_intelligence_service,
    training_planner_service,
    weekly_priority_service,
)
from app.services.knowledge_intelligence_service import (
    initialize_knowledge_intelligence,
)


class MatchEvidenceIntelligenceSyncTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db_path=Path(self.tmp.name)/"match-evidence-sync.db"
        self.originals=[]

        def connection():
            conn=sqlite3.connect(self.db_path)
            conn.row_factory=sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            return conn

        modules=(
            knowledge_repository,
            knowledge_intelligence_repository,
            knowledge_intelligence_schema,
            knowledge_intelligence_adapters,
            match_evidence_repository,
            pattern_intelligence_repository,
            pattern_intelligence_aggregator,
            training_planner_repository,
            weekly_priority_repository,
        )
        for module in modules:
            self.originals.append(
                (
                    module,
                    getattr(module,"get_connection",None),
                    getattr(module,"USE_POSTGRES",None),
                )
            )
            if hasattr(module,"get_connection"):
                module.get_connection=connection
            if hasattr(module,"USE_POSTGRES"):
                module.USE_POSTGRES=False

        conn=connection()
        conn.execute("CREATE TABLE users(id INTEGER PRIMARY KEY,email TEXT)")
        conn.executemany(
            "INSERT INTO users VALUES(?,?)",
            [(1,"one@test.it"),(2,"two@test.it")],
        )
        conn.execute(
            "CREATE TABLE saved_matches("
            "id INTEGER PRIMARY KEY,user_id INTEGER,match_id INTEGER,home TEXT,"
            "away TEXT,league TEXT,created_at TEXT)"
        )
        conn.execute(
            "CREATE TABLE voice_coach_observations("
            "id INTEGER PRIMARY KEY,user_id INTEGER,client_id TEXT,match_key TEXT,"
            "match_id TEXT,minute INTEGER,match_phase TEXT,tactical_topic TEXT,"
            "topic_label TEXT,zone TEXT,polarity TEXT,priority TEXT,player_ids TEXT,"
            "original_text TEXT,status TEXT,created_at TEXT)"
        )
        conn.execute(
            "CREATE TABLE video_reports("
            "id INTEGER PRIMARY KEY,user_id INTEGER,title TEXT,focus TEXT,"
            "observed_team TEXT,frames_analyzed INTEGER,created_at TEXT)"
        )
        conn.execute(
            "CREATE TABLE video_frame_feedback("
            "id INTEGER PRIMARY KEY,user_id INTEGER,video_asset_id INTEGER,"
            "report_id INTEGER,frame_index INTEGER,frame_time REAL,status TEXT,"
            "requested_phase TEXT,detected_phase TEXT,corrected_phase TEXT,"
            "confidence REAL,notes TEXT,created_at TEXT)"
        )
        conn.commit()
        conn.close()

        knowledge_service.initialize_foundation()
        initialize_knowledge_intelligence()
        pattern_intelligence_service.initialize_pattern_intelligence()
        weekly_priority_repository.initialize_weekly_priority_schema()
        training_planner_service.initialize_training_planner()
        match_evidence_service.initialize_match_evidence()

    def tearDown(self):
        for module,connection,use_postgres in self.originals:
            if connection is not None:
                module.get_connection=connection
            if use_postgres is not None:
                module.USE_POSTGRES=use_postgres
        self.tmp.cleanup()

    def request(self,index):
        played=(date.today()-timedelta(days=3-index)).isoformat()
        return MatchEvidenceFinalizeRequest(
            source_match_id=f"coach-match-{index}",
            team_id="team-1",
            season_id="2026-2027",
            competition="Promozione",
            opponent=f"Rivale {index}",
            match_date=played,
            match={
                "result":{"score":"1-0"},
                "formation":{"home":"4-3-3"},
                "module":"4-3-3",
                "players":[],
                "timeline_events":[
                    {
                        "id":f"event-{index}",
                        "type":"palla_persa",
                        "note":"Palla persa centrale",
                        "zone":"central",
                        "minute":30,
                    }
                ],
                "substitutions":[],
                "cards":[],
                "goals":[],
            },
            coach={
                "notes":[],
                "observations":[],
                "ratings":[],
                "final_report":f"Report partita {index}",
            },
            voice_coach={"observation_ids":[]},
            video_ai={"video_report_ids":[],"reviewed_frame_ids":[]},
            metadata={
                "coach_version":"10535",
                "schema_version":1,
                "source":"coach_pwa",
                "flags":{},
            },
        )

    def scalar(self,sql,params=()):
        conn=knowledge_repository.get_connection()
        value=conn.execute(sql,params).fetchone()[0]
        conn.close()
        return value

    def test_finalize_syncs_knowledge_then_pattern_with_canonical_id(self):
        item,created=match_evidence_service.finalize(1,self.request(1))
        canonical_id=item["canonical_match_id"]
        self.assertTrue(created)

        workspace=knowledge_repository.get_or_create_workspace(1)
        nodes=knowledge_intelligence_repository.list_nodes(int(workspace["id"]))
        canonical_nodes=[
            node for node in nodes
            if node["source_type"]=="match_evidence"
        ]
        self.assertEqual(len(canonical_nodes),1)
        self.assertEqual(canonical_nodes[0]["source_id"],canonical_id)
        self.assertEqual(canonical_nodes[0]["match_id"],canonical_id)

        bundle=pattern_intelligence_aggregator.collect_sources(1,[],120)
        self.assertEqual(bundle["matches"][0]["id"],canonical_id)
        self.assertTrue(bundle["evidence"])
        self.assertTrue(
            all(entry["match_id"]==canonical_id for entry in bundle["evidence"])
        )

    def test_double_finalize_is_idempotent_without_duplicates(self):
        first,_=match_evidence_service.finalize(1,self.request(1))
        run_count=self.scalar("SELECT COUNT(*) FROM pattern_intelligence_runs")
        second,created=match_evidence_service.finalize(1,self.request(1))

        self.assertFalse(created)
        self.assertEqual(first["canonical_match_id"],second["canonical_match_id"])
        self.assertEqual(
            self.scalar("SELECT COUNT(*) FROM match_evidence"),
            1,
        )
        self.assertEqual(
            self.scalar(
                "SELECT COUNT(*) FROM knowledge_nodes "
                "WHERE source_type='match_evidence'"
            ),
            1,
        )
        self.assertEqual(
            self.scalar("SELECT COUNT(*) FROM pattern_intelligence_runs"),
            run_count,
        )
        self.assertEqual(
            self.scalar(
                "SELECT COUNT(*) FROM knowledge_source_links "
                "WHERE source_type='match_evidence' AND source_id=?",
                (first["canonical_match_id"],),
            ),
            1,
        )

    def test_three_finalized_matches_create_established_pattern_automatically(self):
        canonical_ids=[]
        for index in range(1,4):
            item,_=match_evidence_service.finalize(1,self.request(index))
            canonical_ids.append(item["canonical_match_id"])

        data=pattern_intelligence_repository.list_patterns(
            1,
            {"page":1,"page_size":50},
        )
        self.assertEqual(data["items"][0]["status"],"established")
        self.assertEqual(data["items"][0]["matches_count"],3)
        evidence=pattern_intelligence_repository.get_pattern(
            1,
            data["items"][0]["id"],
            1,
            20,
        )["evidence"]["items"]
        self.assertEqual(
            {entry["match_id"] for entry in evidence},
            set(canonical_ids),
        )
        priorities=weekly_priority_repository.list_latest(1)
        self.assertEqual(len(priorities),1)
        self.assertEqual(
            set(priorities[0]["canonical_match_ids"]),
            set(canonical_ids),
        )
        self.assertEqual(priorities[0]["status"],"PROPOSED")

        match_evidence_service.finalize(1,self.request(3))
        self.assertEqual(
            self.scalar("SELECT COUNT(*) FROM weekly_priorities"),
            1,
        )

    def test_confirmed_priority_creates_one_idempotent_training_draft(self):
        for index in range(1,4):
            match_evidence_service.finalize(1,self.request(index))

        priority=weekly_priority_repository.list_latest(1)[0]
        first=weekly_priority_service.set_staff_status(
            1,
            priority["priority_id"],
            status="CONFIRMED",
            staff_reason="Priorita confermata dallo staff.",
            topic=None,
            phase=None,
            priority_level=None,
        )
        self.assertEqual(first["status"],"CONFIRMED")
        first_plan=training_planner_repository.latest_plan(1)
        self.assertIsNotNone(first_plan)

        weekly_priority_service.set_staff_status(
            1,
            priority["priority_id"],
            status="CONFIRMED",
            staff_reason="Conferma ripetuta.",
            topic=None,
            phase=None,
            priority_level=None,
        )
        second_plan=training_planner_repository.latest_plan(1)
        self.assertEqual(first_plan["id"],second_plan["id"])
        self.assertEqual(
            self.scalar(
                "SELECT COUNT(*) FROM training_plans "
                "WHERE user_id=1 AND status<>'archiviata'"
            ),
            1,
        )

    def test_modified_priority_replaces_draft_without_active_duplicates(self):
        for index in range(1,4):
            match_evidence_service.finalize(1,self.request(index))

        priority=weekly_priority_repository.list_latest(1)[0]
        weekly_priority_service.set_staff_status(
            1,
            priority["priority_id"],
            status="CONFIRMED",
            staff_reason=None,
            topic=None,
            phase=None,
            priority_level=None,
        )
        first_plan=training_planner_repository.latest_plan(1)

        modified=weekly_priority_service.set_staff_status(
            1,
            priority["priority_id"],
            status="MODIFIED",
            staff_reason="Priorita resa piu urgente.",
            topic="Transizione negativa centrale",
            phase="transition_defense",
            priority_level="HIGH",
        )
        second_plan=training_planner_repository.latest_plan(1)

        self.assertEqual(modified["status"],"MODIFIED")
        self.assertNotEqual(first_plan["id"],second_plan["id"])
        self.assertEqual(
            self.scalar(
                "SELECT COUNT(*) FROM training_plans "
                "WHERE user_id=1 AND status<>'archiviata'"
            ),
            1,
        )
        self.assertEqual(
            self.scalar(
                "SELECT COUNT(*) FROM training_plans "
                "WHERE user_id=1 AND status='archiviata'"
            ),
            1,
        )

    def test_staff_confirmed_pattern_refreshes_weekly_priorities(self):
        for index in range(1,4):
            match_evidence_service.finalize(1,self.request(index))

        pattern=pattern_intelligence_repository.list_patterns(
            1,
            {"page":1,"page_size":50},
        )["items"][0]
        conn=knowledge_repository.get_connection()
        conn.execute("DELETE FROM weekly_priorities WHERE user_id=1")
        conn.commit()
        conn.close()
        self.assertEqual(
            weekly_priority_repository.list_latest(1),
            [],
        )

        updated=pattern_intelligence_service.set_status(
            1,
            pattern["id"],
            "confirmed_by_staff",
        )

        self.assertEqual(updated["status"],"confirmed_by_staff")
        self.assertEqual(
            len(weekly_priority_repository.list_latest(1)),
            1,
        )

    def test_pipeline_logs_structured_statuses_with_canonical_match_id(self):
        with self.assertLogs("matchiq.intelligence.pipeline",level="INFO") as logs:
            item,_=match_evidence_service.finalize(1,self.request(1))

        canonical_id=item["canonical_match_id"]
        events=[record.pipeline_event for record in logs.records]
        self.assertTrue(all(event["canonical_match_id"]==canonical_id for event in events))
        self.assertIn("START",{event["status"] for event in events})
        self.assertIn("SUCCESS",{event["status"] for event in events})
        self.assertTrue(
            {
                "match_evidence",
                "knowledge",
                "pattern",
                "weekly_priorities",
                "training_draft",
            }.issubset({event["step"] for event in events})
        )

    def test_local_history_remains_fallback_without_match_evidence(self):
        local_match={
            "id":"legacy-1",
            "savedAt":date.today().isoformat(),
            "match":{
                "homeTeam":"MatchIQ",
                "awayTeam":"Legacy",
                "date":date.today().isoformat(),
            },
            "events":[
                {
                    "id":"legacy-event",
                    "type":"palla_persa",
                    "note":"Palla persa centrale",
                    "minute":30,
                }
            ],
            "ratings":[],
        }
        bundle=pattern_intelligence_aggregator.collect_sources(
            2,
            [local_match],
            120,
        )
        self.assertEqual(bundle["matches"][0]["id"],"coach:legacy-1")
        self.assertEqual(bundle["evidence"][0]["source_type"],"coach_event")


if __name__=="__main__":
    unittest.main()
