from database import USE_POSTGRES, get_connection


def _id_definition() -> str:
    return "SERIAL PRIMARY KEY" if USE_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"


def initialize_schema() -> None:
    conn=get_connection(); cur=conn.cursor(); ident=_id_definition()
    cur.execute(f"""CREATE TABLE IF NOT EXISTS knowledge_nodes (
      id {ident},workspace_id INTEGER NOT NULL,user_id INTEGER NOT NULL,team_profile_id INTEGER,
      node_type TEXT NOT NULL,source_module TEXT NOT NULL,source_type TEXT NOT NULL,source_id TEXT NOT NULL,
      canonical_key TEXT NOT NULL,title TEXT NOT NULL,summary TEXT,occurred_at TEXT,indexed_at TEXT NOT NULL,
      source_updated_at TEXT,reliability_level TEXT NOT NULL,validation_state TEXT NOT NULL,nature TEXT NOT NULL,
      polarity TEXT,tactical_topic TEXT,zone TEXT,player_id TEXT,match_id TEXT,season TEXT,team_name TEXT,
      metadata_json TEXT NOT NULL,search_text TEXT NOT NULL,source_fingerprint TEXT NOT NULL,current_version INTEGER NOT NULL DEFAULT 1,
      is_active INTEGER NOT NULL DEFAULT 1,last_verified_at TEXT,staff_confirmed INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
      UNIQUE(workspace_id,canonical_key),
      FOREIGN KEY(workspace_id) REFERENCES knowledge_workspaces(id) ON DELETE CASCADE,
      FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)""")
    cur.execute(f"""CREATE TABLE IF NOT EXISTS knowledge_edges (
      id {ident},workspace_id INTEGER NOT NULL,from_node_id INTEGER NOT NULL,to_node_id INTEGER NOT NULL,
      relation_type TEXT NOT NULL,direction TEXT NOT NULL DEFAULT 'outgoing',source_type TEXT NOT NULL,source_id TEXT NOT NULL,
      confidence_level TEXT NOT NULL,validation_state TEXT NOT NULL,explanation TEXT,metadata_json TEXT NOT NULL,
      is_active INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
      UNIQUE(workspace_id,from_node_id,to_node_id,relation_type,source_type,source_id),
      FOREIGN KEY(workspace_id) REFERENCES knowledge_workspaces(id) ON DELETE CASCADE,
      FOREIGN KEY(from_node_id) REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
      FOREIGN KEY(to_node_id) REFERENCES knowledge_nodes(id) ON DELETE CASCADE)""")
    cur.execute(f"""CREATE TABLE IF NOT EXISTS knowledge_node_versions (
      id {ident},node_id INTEGER NOT NULL,version_number INTEGER NOT NULL,previous_snapshot_json TEXT,
      snapshot_json TEXT NOT NULL,change_type TEXT NOT NULL,changed_by TEXT NOT NULL,source_updated_at TEXT,
      created_at TEXT NOT NULL,UNIQUE(node_id,version_number),
      FOREIGN KEY(node_id) REFERENCES knowledge_nodes(id) ON DELETE CASCADE)""")
    cur.execute(f"""CREATE TABLE IF NOT EXISTS knowledge_timeline_entries (
      id {ident},workspace_id INTEGER NOT NULL,node_id INTEGER NOT NULL,match_id TEXT,event_type TEXT NOT NULL,
      title TEXT NOT NULL,summary TEXT,occurred_at TEXT NOT NULL,source_module TEXT NOT NULL,source_type TEXT NOT NULL,
      source_id TEXT NOT NULL,tactical_topic TEXT,zone TEXT,reliability_level TEXT NOT NULL,metadata_json TEXT NOT NULL,
      is_active INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL,
      UNIQUE(workspace_id,node_id,event_type,source_type,source_id),
      FOREIGN KEY(workspace_id) REFERENCES knowledge_workspaces(id) ON DELETE CASCADE,
      FOREIGN KEY(node_id) REFERENCES knowledge_nodes(id) ON DELETE CASCADE)""")
    cur.execute(f"""CREATE TABLE IF NOT EXISTS knowledge_tags (
      id {ident},workspace_id INTEGER NOT NULL,name TEXT NOT NULL,canonical_name TEXT NOT NULL,created_at TEXT NOT NULL,
      UNIQUE(workspace_id,canonical_name),FOREIGN KEY(workspace_id) REFERENCES knowledge_workspaces(id) ON DELETE CASCADE)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS knowledge_node_tags (
      node_id INTEGER NOT NULL,tag_id INTEGER NOT NULL,created_at TEXT NOT NULL,PRIMARY KEY(node_id,tag_id),
      FOREIGN KEY(node_id) REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
      FOREIGN KEY(tag_id) REFERENCES knowledge_tags(id) ON DELETE CASCADE)""")
    cur.execute(f"""CREATE TABLE IF NOT EXISTS knowledge_sync_state (
      id {ident},workspace_id INTEGER NOT NULL,user_id INTEGER NOT NULL,module TEXT NOT NULL,status TEXT NOT NULL,
      source_fingerprint TEXT,last_source_updated_at TEXT,last_synced_at TEXT,last_error TEXT,retry_count INTEGER NOT NULL DEFAULT 0,
      lock_token TEXT,locked_at TEXT,metadata_json TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
      UNIQUE(workspace_id,module),FOREIGN KEY(workspace_id) REFERENCES knowledge_workspaces(id) ON DELETE CASCADE,
      FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)""")
    cur.execute(f"""CREATE TABLE IF NOT EXISTS knowledge_staff_notes (
      id {ident},workspace_id INTEGER NOT NULL,node_id INTEGER NOT NULL,user_id INTEGER NOT NULL,note TEXT NOT NULL,
      created_at TEXT NOT NULL,FOREIGN KEY(workspace_id) REFERENCES knowledge_workspaces(id) ON DELETE CASCADE,
      FOREIGN KEY(node_id) REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
      FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)""")
    indexes=(
      "CREATE INDEX IF NOT EXISTS idx_kn_nodes_workspace_type ON knowledge_nodes(workspace_id,node_type,is_active)",
      "CREATE INDEX IF NOT EXISTS idx_kn_nodes_user_source ON knowledge_nodes(user_id,source_type,source_id)",
      "CREATE INDEX IF NOT EXISTS idx_kn_nodes_team ON knowledge_nodes(team_profile_id,team_name)",
      "CREATE INDEX IF NOT EXISTS idx_kn_nodes_match_player ON knowledge_nodes(match_id,player_id)",
      "CREATE INDEX IF NOT EXISTS idx_kn_nodes_topic_zone ON knowledge_nodes(tactical_topic,zone)",
      "CREATE INDEX IF NOT EXISTS idx_kn_nodes_time ON knowledge_nodes(occurred_at,season)",
      "CREATE INDEX IF NOT EXISTS idx_kn_nodes_validation ON knowledge_nodes(validation_state,reliability_level)",
      "CREATE INDEX IF NOT EXISTS idx_kn_edges_from ON knowledge_edges(from_node_id,relation_type,is_active)",
      "CREATE INDEX IF NOT EXISTS idx_kn_edges_to ON knowledge_edges(to_node_id,relation_type,is_active)",
      "CREATE INDEX IF NOT EXISTS idx_kn_timeline_workspace ON knowledge_timeline_entries(workspace_id,occurred_at,is_active)",
      "CREATE INDEX IF NOT EXISTS idx_kn_versions_node ON knowledge_node_versions(node_id,version_number)",
      "CREATE INDEX IF NOT EXISTS idx_kn_sync_workspace ON knowledge_sync_state(workspace_id,status,updated_at)",
    )
    for statement in indexes: cur.execute(statement)
    conn.commit(); conn.close()
