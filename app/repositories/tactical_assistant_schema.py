from database import USE_POSTGRES, get_connection


def _id() -> str:
    return "SERIAL PRIMARY KEY" if USE_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"


def initialize_schema() -> None:
    conn = get_connection(); cur = conn.cursor(); ident = _id()
    cur.execute(f"""CREATE TABLE IF NOT EXISTS tactical_assistant_conversations (
      id {ident},workspace_id INTEGER NOT NULL,user_id INTEGER NOT NULL,team_profile_id INTEGER,
      title TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'active',context_scope_json TEXT NOT NULL,
      context_summary_json TEXT NOT NULL,active_match_id TEXT,active_season TEXT,
      started_at TEXT NOT NULL,last_message_at TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
      FOREIGN KEY(workspace_id) REFERENCES knowledge_workspaces(id) ON DELETE CASCADE,
      FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)""")
    cur.execute(f"""CREATE TABLE IF NOT EXISTS tactical_assistant_messages (
      id {ident},conversation_id INTEGER NOT NULL,role TEXT NOT NULL,content TEXT NOT NULL,intent TEXT,
      structured_query_json TEXT NOT NULL,answer_type TEXT,confidence_level TEXT,
      has_sufficient_evidence INTEGER NOT NULL DEFAULT 0,limitations_json TEXT NOT NULL,
      response_json TEXT NOT NULL,created_at TEXT NOT NULL,
      FOREIGN KEY(conversation_id) REFERENCES tactical_assistant_conversations(id) ON DELETE CASCADE)""")
    cur.execute(f"""CREATE TABLE IF NOT EXISTS tactical_assistant_message_sources (
      id {ident},message_id INTEGER NOT NULL,knowledge_node_id INTEGER NOT NULL,source_type TEXT NOT NULL,
      source_id TEXT NOT NULL,title TEXT NOT NULL,evidence_summary TEXT,reliability_level TEXT,
      objective_or_subjective TEXT,relation_type TEXT,action_url TEXT,created_at TEXT NOT NULL,
      UNIQUE(message_id,knowledge_node_id),
      FOREIGN KEY(message_id) REFERENCES tactical_assistant_messages(id) ON DELETE CASCADE,
      FOREIGN KEY(knowledge_node_id) REFERENCES knowledge_nodes(id) ON DELETE CASCADE)""")
    cur.execute(f"""CREATE TABLE IF NOT EXISTS tactical_assistant_feedback (
      id {ident},message_id INTEGER NOT NULL,user_id INTEGER NOT NULL,rating INTEGER,feedback_type TEXT NOT NULL,
      note TEXT,created_at TEXT NOT NULL,UNIQUE(message_id,user_id),
      FOREIGN KEY(message_id) REFERENCES tactical_assistant_messages(id) ON DELETE CASCADE,
      FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)""")
    cur.execute(f"""CREATE TABLE IF NOT EXISTS tactical_assistant_telemetry (
      id {ident},workspace_id INTEGER NOT NULL,user_id INTEGER NOT NULL,conversation_id INTEGER,
      intent TEXT,outcome TEXT NOT NULL,source_count INTEGER NOT NULL DEFAULT 0,latency_ms INTEGER NOT NULL DEFAULT 0,
      provider TEXT,model TEXT,error_code TEXT,estimated_tokens INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL,
      FOREIGN KEY(workspace_id) REFERENCES knowledge_workspaces(id) ON DELETE CASCADE,
      FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)""")
    for sql in (
      "CREATE INDEX IF NOT EXISTS idx_ta_conversations_owner ON tactical_assistant_conversations(workspace_id,user_id,status,updated_at)",
      "CREATE INDEX IF NOT EXISTS idx_ta_conversations_team ON tactical_assistant_conversations(team_profile_id,active_match_id,active_season)",
      "CREATE INDEX IF NOT EXISTS idx_ta_messages_conversation ON tactical_assistant_messages(conversation_id,created_at)",
      "CREATE INDEX IF NOT EXISTS idx_ta_messages_intent ON tactical_assistant_messages(intent,created_at)",
      "CREATE INDEX IF NOT EXISTS idx_ta_sources_message ON tactical_assistant_message_sources(message_id,source_type)",
      "CREATE INDEX IF NOT EXISTS idx_ta_feedback_message ON tactical_assistant_feedback(message_id,user_id)",
      "CREATE INDEX IF NOT EXISTS idx_ta_telemetry_rate ON tactical_assistant_telemetry(user_id,created_at)",
    ): cur.execute(sql)
    conn.commit(); conn.close()
