import json
from typing import Any, Dict, List, Optional

from database import USE_POSTGRES, fetchall, fetchone, get_connection, get_last_insert_id, q, utc_now


def _id_definition() -> str:
    return "SERIAL PRIMARY KEY" if USE_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"


def initialize_training_schema() -> None:
    conn=get_connection(); cur=conn.cursor(); ident=_id_definition()
    cur.execute("""CREATE TABLE IF NOT EXISTS training_exercises (
      id TEXT PRIMARY KEY,title TEXT NOT NULL,category TEXT NOT NULL,tactical_theme TEXT NOT NULL,objective TEXT NOT NULL,
      min_players INTEGER NOT NULL,max_players INTEGER NOT NULL,goalkeepers INTEGER NOT NULL,duration INTEGER NOT NULL,
      intensity TEXT NOT NULL,difficulty TEXT NOT NULL,source TEXT NOT NULL,reliability_level TEXT NOT NULL,
      validation_status TEXT NOT NULL,version TEXT NOT NULL,payload TEXT NOT NULL,updated_at TEXT NOT NULL)""")
    cur.execute(f"""CREATE TABLE IF NOT EXISTS training_plans (
      id {ident},workspace_id INTEGER NOT NULL,user_id INTEGER NOT NULL,week_key TEXT NOT NULL,status TEXT NOT NULL,
      training_days TEXT NOT NULL,priorities TEXT NOT NULL,sources TEXT NOT NULL,original_plan TEXT NOT NULL,current_plan TEXT NOT NULL,
      source_fingerprint TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1,is_viewed INTEGER NOT NULL DEFAULT 0,
      staff_note TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,archived_at TEXT,
      FOREIGN KEY(workspace_id) REFERENCES knowledge_workspaces(id) ON DELETE CASCADE,
      FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)""")
    cur.execute(f"""CREATE TABLE IF NOT EXISTS training_plan_history (
      id {ident},plan_id INTEGER NOT NULL,user_id INTEGER NOT NULL,action TEXT NOT NULL,snapshot TEXT NOT NULL,note TEXT,created_at TEXT NOT NULL,
      FOREIGN KEY(plan_id) REFERENCES training_plans(id) ON DELETE CASCADE,
      FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_training_library_theme ON training_exercises(tactical_theme,category,validation_status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_training_plans_user_week ON training_plans(user_id,week_key,updated_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_training_plans_workspace_status ON training_plans(workspace_id,status,updated_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_training_history_plan ON training_plan_history(plan_id,created_at)")
    conn.commit(); conn.close()


def seed_library(items: List[Dict[str,Any]]) -> None:
    now=utc_now(); conn=get_connection(); cur=conn.cursor()
    for item in items:
        values=(item["id"],item["title"],item["category"],item["tactical_theme"],item["objective"],item["min_players"],item["max_players"],item["goalkeepers"],item["duration"],item["intensity"],item["difficulty"],item["source"],item["reliability_level"],item["validation_status"],item["version"],json.dumps(item,ensure_ascii=False),now)
        cur.execute(q("""INSERT INTO training_exercises
          (id,title,category,tactical_theme,objective,min_players,max_players,goalkeepers,duration,intensity,difficulty,source,reliability_level,validation_status,version,payload,updated_at)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET title=excluded.title,category=excluded.category,tactical_theme=excluded.tactical_theme,objective=excluded.objective,min_players=excluded.min_players,max_players=excluded.max_players,goalkeepers=excluded.goalkeepers,duration=excluded.duration,intensity=excluded.intensity,difficulty=excluded.difficulty,source=excluded.source,reliability_level=excluded.reliability_level,validation_status=excluded.validation_status,version=excluded.version,payload=excluded.payload,updated_at=excluded.updated_at"""),values)
    conn.commit(); conn.close()


def _loads(value: Any,fallback: Any) -> Any:
    if isinstance(value,(dict,list)): return value
    try: return json.loads(value) if value else fallback
    except (TypeError,ValueError): return fallback


def _decode(row: Optional[Dict[str,Any]]) -> Optional[Dict[str,Any]]:
    if not row: return None
    data=dict(row)
    for field in ("training_days","priorities","sources","original_plan","current_plan","payload","snapshot"):
        if field in data: data[field]=_loads(data[field],[] if field in {"training_days","priorities","sources"} else {})
    if "is_viewed" in data: data["is_viewed"]=bool(data["is_viewed"])
    return data


def list_exercises(theme: str=None,limit: int=50) -> List[Dict[str,Any]]:
    conn=get_connection(); cur=conn.cursor()
    if theme: cur.execute(q("SELECT * FROM training_exercises WHERE tactical_theme=? AND validation_status<>'archived' ORDER BY title LIMIT ?"),(theme,limit))
    else: cur.execute(q("SELECT * FROM training_exercises WHERE validation_status<>'archived' ORDER BY tactical_theme,title LIMIT ?"),(limit,))
    rows=[_decode(row)["payload"] for row in fetchall(cur)]; conn.close(); return rows


def latest_plan(user_id: int,include_archived: bool=False) -> Optional[Dict[str,Any]]:
    conn=get_connection(); cur=conn.cursor(); clause="" if include_archived else " AND status<>'archiviata'"
    cur.execute(q(f"SELECT * FROM training_plans WHERE user_id=?{clause} ORDER BY updated_at DESC,id DESC LIMIT 1"),(user_id,)); row=fetchone(cur); conn.close(); return _decode(row)


def get_plan(user_id: int,plan_id: int) -> Optional[Dict[str,Any]]:
    conn=get_connection(); cur=conn.cursor(); cur.execute(q("SELECT * FROM training_plans WHERE id=? AND user_id=?"),(plan_id,user_id)); row=fetchone(cur); conn.close(); return _decode(row)


def save_plan(user_id: int,workspace_id: int,week_key: str,days: list,priorities: list,sources: list,plan: Dict[str,Any],fingerprint: str,status: str="proposta_ai",version: int=1) -> Dict[str,Any]:
    now=utc_now(); returning=" RETURNING id" if USE_POSTGRES else ""; conn=get_connection(); cur=conn.cursor()
    cur.execute(q(f"""INSERT INTO training_plans
      (workspace_id,user_id,week_key,status,training_days,priorities,sources,original_plan,current_plan,source_fingerprint,version,is_viewed,created_at,updated_at)
      VALUES (?,?,?,?,?,?,?,?,?,?,?,0,?,?){returning}"""),(workspace_id,user_id,week_key,status,json.dumps(days,ensure_ascii=False),json.dumps(priorities,ensure_ascii=False),json.dumps(sources,ensure_ascii=False),json.dumps(plan,ensure_ascii=False),json.dumps(plan,ensure_ascii=False),fingerprint,version,now,now))
    plan_id=get_last_insert_id(cur); conn.commit(); conn.close(); item=get_plan(user_id,plan_id); add_history(user_id,plan_id,"created",item,None); return item


def add_history(user_id: int,plan_id: int,action: str,snapshot: Dict[str,Any],note: Optional[str]) -> None:
    conn=get_connection(); cur=conn.cursor(); cur.execute(q("INSERT INTO training_plan_history(plan_id,user_id,action,snapshot,note,created_at) VALUES(?,?,?,?,?,?)"),(plan_id,user_id,action,json.dumps(snapshot or {},ensure_ascii=False,default=str),note,utc_now())); conn.commit(); conn.close()


def update_plan(user_id: int,plan_id: int,current: Optional[Dict[str,Any]]=None,status: Optional[str]=None,note: Optional[str]=None,action: str="modified") -> Optional[Dict[str,Any]]:
    existing=get_plan(user_id,plan_id)
    if not existing: return None
    fields=[]; params=[]
    if current is not None: fields.extend(["current_plan=?","version=version+1"]); params.append(json.dumps(current,ensure_ascii=False))
    if status is not None: fields.append("status=?"); params.append(status)
    if note is not None: fields.append("staff_note=?"); params.append(note)
    fields.append("updated_at=?"); params.append(utc_now())
    if status=="archiviata": fields.append("archived_at=?"); params.append(utc_now())
    params.extend([plan_id,user_id]); conn=get_connection(); cur=conn.cursor(); cur.execute(q(f"UPDATE training_plans SET {','.join(fields)} WHERE id=? AND user_id=?"),params); conn.commit(); conn.close(); item=get_plan(user_id,plan_id); add_history(user_id,plan_id,action,item,note); return item


def mark_viewed(user_id: int,plan_id: int) -> Optional[Dict[str,Any]]:
    conn=get_connection(); cur=conn.cursor(); cur.execute(q("UPDATE training_plans SET is_viewed=1,updated_at=? WHERE id=? AND user_id=?"),(utc_now(),plan_id,user_id)); conn.commit(); conn.close(); return get_plan(user_id,plan_id)


def history(user_id: int,plan_id: int) -> List[Dict[str,Any]]:
    if not get_plan(user_id,plan_id): return []
    conn=get_connection(); cur=conn.cursor(); cur.execute(q("SELECT * FROM training_plan_history WHERE plan_id=? AND user_id=? ORDER BY created_at,id"),(plan_id,user_id)); rows=[_decode(row) for row in fetchall(cur)]; conn.close(); return rows
