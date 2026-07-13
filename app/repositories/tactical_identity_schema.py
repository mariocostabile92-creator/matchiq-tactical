from database import USE_POSTGRES, get_connection


def _id() -> str:
    return "SERIAL PRIMARY KEY" if USE_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"


def initialize_schema() -> None:
    conn = get_connection(); cur = conn.cursor(); ident = _id()
    cur.execute(f"""CREATE TABLE IF NOT EXISTS tactical_identity_profiles (
      id {ident},workspace_id INTEGER NOT NULL,user_id INTEGER NOT NULL,team_profile_id INTEGER,coach_profile_id INTEGER,
      season TEXT NOT NULL DEFAULT '',period_start TEXT NOT NULL DEFAULT '',period_end TEXT NOT NULL DEFAULT '',competition TEXT NOT NULL DEFAULT '',
      formation TEXT NOT NULL DEFAULT '',source_type TEXT NOT NULL DEFAULT '',status TEXT NOT NULL,
      source_fingerprint TEXT NOT NULL,matches_analyzed INTEGER NOT NULL DEFAULT 0,sources_analyzed INTEGER NOT NULL DEFAULT 0,
      identity_version INTEGER NOT NULL DEFAULT 1,overall_confidence TEXT NOT NULL DEFAULT 'bassa',summary_json TEXT NOT NULL,
      filters_json TEXT NOT NULL,processing_error TEXT,lock_token TEXT,locked_at TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
      UNIQUE(workspace_id,user_id,team_profile_id,season,period_start,period_end),
      FOREIGN KEY(workspace_id) REFERENCES knowledge_workspaces(id) ON DELETE CASCADE,
      FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)""")
    cur.execute(f"""CREATE TABLE IF NOT EXISTS tactical_identity_dimensions (
      id {ident},identity_profile_id INTEGER NOT NULL,dimension_type TEXT NOT NULL,dimension_group TEXT NOT NULL,label TEXT NOT NULL,
      declared_value TEXT,declared_source_json TEXT NOT NULL DEFAULT '{{}}',observed_value TEXT,validated_value TEXT,declared_strength TEXT,observed_strength TEXT,
      alignment_state TEXT NOT NULL,confidence_level TEXT NOT NULL,trend_direction TEXT NOT NULL,evidence_count INTEGER NOT NULL DEFAULT 0,
      match_count INTEGER NOT NULL DEFAULT 0,explanation TEXT NOT NULL,limitations_json TEXT NOT NULL,validation_state TEXT NOT NULL,
      distribution_json TEXT NOT NULL,previous_period_json TEXT NOT NULL,recent_period_json TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
      UNIQUE(identity_profile_id,dimension_type),FOREIGN KEY(identity_profile_id) REFERENCES tactical_identity_profiles(id) ON DELETE CASCADE)""")
    cur.execute(f"""CREATE TABLE IF NOT EXISTS tactical_identity_evidence (
      id {ident},identity_dimension_id INTEGER NOT NULL,knowledge_node_id INTEGER NOT NULL,source_type TEXT NOT NULL,source_id TEXT NOT NULL,
      match_id TEXT,player_id TEXT,topic TEXT,zone TEXT,phase TEXT,evidence_summary TEXT NOT NULL,evidence_nature TEXT NOT NULL,
      reliability_level TEXT NOT NULL,evidence_weight REAL NOT NULL DEFAULT 0,occurred_at TEXT,created_at TEXT NOT NULL,
      UNIQUE(identity_dimension_id,knowledge_node_id),FOREIGN KEY(identity_dimension_id) REFERENCES tactical_identity_dimensions(id) ON DELETE CASCADE)""")
    cur.execute(f"""CREATE TABLE IF NOT EXISTS tactical_identity_versions (
      id {ident},identity_profile_id INTEGER NOT NULL,version_number INTEGER NOT NULL,snapshot_json TEXT NOT NULL,
      change_summary TEXT NOT NULL,change_reason TEXT NOT NULL,changed_by TEXT NOT NULL,created_at TEXT NOT NULL,
      UNIQUE(identity_profile_id,version_number),FOREIGN KEY(identity_profile_id) REFERENCES tactical_identity_profiles(id) ON DELETE CASCADE)""")
    cur.execute(f"""CREATE TABLE IF NOT EXISTS tactical_identity_staff_feedback (
      id {ident},identity_dimension_id INTEGER NOT NULL,user_id INTEGER NOT NULL,action TEXT NOT NULL,note TEXT,declared_value TEXT,created_at TEXT NOT NULL,
      FOREIGN KEY(identity_dimension_id) REFERENCES tactical_identity_dimensions(id) ON DELETE CASCADE,
      FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)""")
    migrations = (
      ("tactical_identity_profiles", "competition", "TEXT NOT NULL DEFAULT ''"),
      ("tactical_identity_profiles", "formation", "TEXT NOT NULL DEFAULT ''"),
      ("tactical_identity_profiles", "source_type", "TEXT NOT NULL DEFAULT ''"),
      ("tactical_identity_dimensions", "declared_source_json", "TEXT NOT NULL DEFAULT '{}'"),
    )
    for table,column,definition in migrations:
        try:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            conn.commit()
        except Exception:
            conn.rollback()
            cur=conn.cursor()
    indexes = (
      "CREATE INDEX IF NOT EXISTS idx_ti_profile_scope ON tactical_identity_profiles(workspace_id,user_id,team_profile_id,season,period_start,period_end)",
      "CREATE INDEX IF NOT EXISTS idx_ti_profile_filters ON tactical_identity_profiles(competition,formation,source_type)",
      "CREATE INDEX IF NOT EXISTS idx_ti_profile_status ON tactical_identity_profiles(status,source_fingerprint,updated_at)",
      "CREATE INDEX IF NOT EXISTS idx_ti_dimension_group ON tactical_identity_dimensions(identity_profile_id,dimension_group,confidence_level,validation_state)",
      "CREATE INDEX IF NOT EXISTS idx_ti_evidence_source ON tactical_identity_evidence(source_type,source_id,match_id,player_id)",
      "CREATE INDEX IF NOT EXISTS idx_ti_evidence_node ON tactical_identity_evidence(knowledge_node_id,topic,occurred_at)",
      "CREATE INDEX IF NOT EXISTS idx_ti_feedback_dimension ON tactical_identity_staff_feedback(identity_dimension_id,user_id,created_at)",
      "CREATE INDEX IF NOT EXISTS idx_ti_versions_profile ON tactical_identity_versions(identity_profile_id,version_number)",
    )
    for statement in indexes: cur.execute(statement)
    conn.commit(); conn.close()
