from database import USE_POSTGRES, get_connection


def _id() -> str:
    return "SERIAL PRIMARY KEY" if USE_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"


def initialize_schema() -> None:
    conn = get_connection(); cur = conn.cursor(); ident = _id()
    cur.execute(f"""CREATE TABLE IF NOT EXISTS decision_engine_cases (
      id {ident},workspace_id INTEGER NOT NULL,user_id INTEGER NOT NULL,team_profile_id INTEGER,match_id TEXT,
      phase TEXT NOT NULL,minute INTEGER,score_state TEXT,prompt TEXT,situation_summary TEXT NOT NULL,status TEXT NOT NULL,
      evidence_state TEXT NOT NULL,source_fingerprint TEXT NOT NULL,source_context_json TEXT NOT NULL,limitations_json TEXT NOT NULL,
      created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
      UNIQUE(workspace_id,user_id,source_fingerprint),
      FOREIGN KEY(workspace_id) REFERENCES knowledge_workspaces(id) ON DELETE CASCADE,
      FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)""")
    cur.execute(f"""CREATE TABLE IF NOT EXISTS decision_engine_options (
      id {ident},case_id INTEGER NOT NULL,option_type TEXT NOT NULL,title TEXT NOT NULL,summary TEXT NOT NULL,
      tactical_changes_json TEXT NOT NULL,player_changes_json TEXT NOT NULL,formation_changes_json TEXT NOT NULL,
      benefits_json TEXT NOT NULL,risks_json TEXT NOT NULL,prerequisites_json TEXT NOT NULL,
      confidence_level TEXT NOT NULL,suitability_score INTEGER NOT NULL,identity_alignment TEXT NOT NULL,
      evidence_summary TEXT NOT NULL,limitations_json TEXT NOT NULL,rank_order INTEGER NOT NULL,status TEXT NOT NULL,
      created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
      UNIQUE(case_id,rank_order),FOREIGN KEY(case_id) REFERENCES decision_engine_cases(id) ON DELETE CASCADE)""")
    cur.execute(f"""CREATE TABLE IF NOT EXISTS decision_engine_option_sources (
      id {ident},option_id INTEGER NOT NULL,knowledge_node_id INTEGER,source_type TEXT NOT NULL,source_id TEXT NOT NULL,
      title TEXT NOT NULL,summary TEXT NOT NULL,reliability_level TEXT NOT NULL,relation_type TEXT NOT NULL,action_url TEXT,
      created_at TEXT NOT NULL,UNIQUE(option_id,source_type,source_id),
      FOREIGN KEY(option_id) REFERENCES decision_engine_options(id) ON DELETE CASCADE)""")
    cur.execute(f"""CREATE TABLE IF NOT EXISTS decision_engine_staff_decisions (
      id {ident},case_id INTEGER NOT NULL,option_id INTEGER,user_id INTEGER NOT NULL,action TEXT NOT NULL,note TEXT,
      executed_manually INTEGER NOT NULL DEFAULT 0,execution_reference TEXT,created_at TEXT NOT NULL,
      FOREIGN KEY(case_id) REFERENCES decision_engine_cases(id) ON DELETE CASCADE,
      FOREIGN KEY(option_id) REFERENCES decision_engine_options(id) ON DELETE SET NULL,
      FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)""")
    cur.execute(f"""CREATE TABLE IF NOT EXISTS decision_engine_outcomes (
      id {ident},staff_decision_id INTEGER NOT NULL,summary TEXT NOT NULL,evidence_json TEXT NOT NULL,
      relation_state TEXT NOT NULL,confidence_level TEXT NOT NULL,created_at TEXT NOT NULL,
      FOREIGN KEY(staff_decision_id) REFERENCES decision_engine_staff_decisions(id) ON DELETE CASCADE)""")
    cur.execute(f"""CREATE TABLE IF NOT EXISTS decision_engine_telemetry (
      id {ident},workspace_id INTEGER NOT NULL,user_id INTEGER NOT NULL,case_id INTEGER,event_type TEXT NOT NULL,
      duration_ms INTEGER,source_count INTEGER NOT NULL DEFAULT 0,option_count INTEGER NOT NULL DEFAULT 0,
      metadata_json TEXT NOT NULL,created_at TEXT NOT NULL,
      FOREIGN KEY(workspace_id) REFERENCES knowledge_workspaces(id) ON DELETE CASCADE,
      FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)""")
    # Commit the base schema before any optional/index work. PostgreSQL rolls
    # back DDL in the same transaction when a later statement fails.
    conn.commit()
    indexes = (
      "CREATE INDEX IF NOT EXISTS idx_decision_cases_owner ON decision_engine_cases(workspace_id,user_id,created_at)",
      "CREATE INDEX IF NOT EXISTS idx_decision_cases_context ON decision_engine_cases(team_profile_id,match_id,phase,status)",
      "CREATE INDEX IF NOT EXISTS idx_decision_options_case ON decision_engine_options(case_id,rank_order,status)",
      "CREATE INDEX IF NOT EXISTS idx_decision_sources_option ON decision_engine_option_sources(option_id,reliability_level)",
      "CREATE INDEX IF NOT EXISTS idx_decision_staff_case ON decision_engine_staff_decisions(case_id,user_id,created_at)",
      "CREATE INDEX IF NOT EXISTS idx_decision_outcomes_staff ON decision_engine_outcomes(staff_decision_id,created_at)",
      "CREATE INDEX IF NOT EXISTS idx_decision_telemetry_owner ON decision_engine_telemetry(workspace_id,user_id,created_at)",
    )
    for statement in indexes: cur.execute(statement)
    conn.commit(); conn.close()
