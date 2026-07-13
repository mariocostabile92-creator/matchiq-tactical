from database import USE_POSTGRES, get_connection


def initialize_schema() -> None:
    ident = "SERIAL PRIMARY KEY" if USE_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""CREATE TABLE IF NOT EXISTS club_intelligence_clubs (
        id {ident}, owner_user_id INTEGER NOT NULL, name TEXT NOT NULL, season TEXT,
        declared_philosophy TEXT, technical_principles_json TEXT NOT NULL DEFAULT '[]',
        transition_principles_json TEXT NOT NULL DEFAULT '[]', set_piece_principles_json TEXT NOT NULL DEFAULT '[]',
        sharing_policy_json TEXT NOT NULL DEFAULT '{{}}', status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    )""")
    cur.execute(f"""CREATE TABLE IF NOT EXISTS club_intelligence_teams (
        id {ident}, club_id INTEGER NOT NULL, knowledge_workspace_id INTEGER,
        workspace_owner_user_id INTEGER, name TEXT NOT NULL, category TEXT, age_group TEXT, season TEXT,
        team_type TEXT NOT NULL DEFAULT 'other', level_order INTEGER NOT NULL DEFAULT 100,
        sharing_scope TEXT NOT NULL DEFAULT 'private', status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        FOREIGN KEY(club_id) REFERENCES club_intelligence_clubs(id) ON DELETE CASCADE
    )""")
    cur.execute(f"""CREATE TABLE IF NOT EXISTS club_intelligence_memberships (
        id {ident}, club_id INTEGER NOT NULL, user_id INTEGER NOT NULL, role TEXT NOT NULL,
        team_ids_json TEXT NOT NULL DEFAULT '[]', permissions_json TEXT NOT NULL DEFAULT '{{}}',
        status TEXT NOT NULL DEFAULT 'active', invited_by INTEGER, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        UNIQUE(club_id,user_id), FOREIGN KEY(club_id) REFERENCES club_intelligence_clubs(id) ON DELETE CASCADE
    )""")
    cur.execute(f"""CREATE TABLE IF NOT EXISTS club_intelligence_principles (
        id {ident}, club_id INTEGER NOT NULL, title TEXT NOT NULL, principle_area TEXT NOT NULL,
        description TEXT NOT NULL, source_kind TEXT NOT NULL, validation_state TEXT NOT NULL,
        team_ids_json TEXT NOT NULL DEFAULT '[]', owner_user_id INTEGER NOT NULL,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        FOREIGN KEY(club_id) REFERENCES club_intelligence_clubs(id) ON DELETE CASCADE
    )""")
    cur.execute(f"""CREATE TABLE IF NOT EXISTS club_intelligence_resources (
        id {ident}, club_id INTEGER NOT NULL, source_workspace_id INTEGER NOT NULL, source_node_id INTEGER NOT NULL,
        shared_by INTEGER NOT NULL, resource_type TEXT NOT NULL, title TEXT NOT NULL, target_scope TEXT NOT NULL,
        allowed_team_ids_json TEXT NOT NULL DEFAULT '[]', purpose TEXT, status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        UNIQUE(club_id,source_workspace_id,source_node_id),
        FOREIGN KEY(club_id) REFERENCES club_intelligence_clubs(id) ON DELETE CASCADE
    )""")
    cur.execute(f"""CREATE TABLE IF NOT EXISTS club_intelligence_snapshots (
        id {ident}, club_id INTEGER NOT NULL, requested_by INTEGER NOT NULL, period_label TEXT,
        team_ids_json TEXT NOT NULL DEFAULT '[]', summary_json TEXT NOT NULL DEFAULT '{{}}',
        sources_json TEXT NOT NULL DEFAULT '[]', limitations_json TEXT NOT NULL DEFAULT '[]',
        status TEXT NOT NULL DEFAULT 'ready', created_at TEXT NOT NULL,
        FOREIGN KEY(club_id) REFERENCES club_intelligence_clubs(id) ON DELETE CASCADE
    )""")
    cur.execute(f"""CREATE TABLE IF NOT EXISTS club_intelligence_audit (
        id {ident}, club_id INTEGER NOT NULL, actor_user_id INTEGER NOT NULL, action TEXT NOT NULL,
        entity_type TEXT NOT NULL, entity_id TEXT, metadata_json TEXT NOT NULL DEFAULT '{{}}', created_at TEXT NOT NULL,
        FOREIGN KEY(club_id) REFERENCES club_intelligence_clubs(id) ON DELETE CASCADE
    )""")
    conn.commit()
    for statement in (
        "CREATE INDEX IF NOT EXISTS idx_club_members_user ON club_intelligence_memberships(user_id,status)",
        "CREATE INDEX IF NOT EXISTS idx_club_teams_club ON club_intelligence_teams(club_id,status,level_order)",
        "CREATE INDEX IF NOT EXISTS idx_club_resources_club ON club_intelligence_resources(club_id,status)",
        "CREATE INDEX IF NOT EXISTS idx_club_snapshots_club ON club_intelligence_snapshots(club_id,created_at)",
    ):
        cur.execute(statement)
    conn.commit()
    conn.close()
