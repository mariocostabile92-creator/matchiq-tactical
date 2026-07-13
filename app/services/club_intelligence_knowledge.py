from app.repositories import knowledge_intelligence_repository as knowledge_repository


def publish_club(workspace_id: int, user_id: int, club: dict) -> dict:
    return knowledge_repository.upsert_node(workspace_id, user_id, "club_profile", "club_intelligence", "club_profile", str(club["id"]), {
        "title": club["name"], "summary": club.get("declared_philosophy") or "Profilo tecnico del club.", "season": club.get("season"),
        "reliability_level": "alta", "validation_state": "declared_by_club", "nature": "dichiarazione_club", "metadata": {"club_id": club["id"]}, "tags": ["club", "filosofia"],
    })


def publish_team(workspace_id: int, user_id: int, club_node: dict, team: dict) -> dict:
    node = knowledge_repository.upsert_node(workspace_id, user_id, "club_team", "club_intelligence", "club_team", str(team["id"]), {
        "title": team["name"], "summary": f"{team.get('category') or 'Categoria non indicata'} - contesto tecnico autonomo.", "season": team.get("season"), "team_name": team["name"],
        "reliability_level": "alta", "validation_state": "staff_configured", "nature": "configurazione_staff", "metadata": {"club_id": team["club_id"], "knowledge_workspace_id": team.get("knowledge_workspace_id")}, "tags": [team.get("category") or "squadra"],
    })
    knowledge_repository.upsert_edge(workspace_id, node, club_node, "belongs_to", "club_team", str(team["id"]), "La squadra appartiene al club ma conserva il proprio contesto.", "alta", "staff_configured", {})
    return node


def publish_principle(workspace_id: int, user_id: int, club_node: dict, principle: dict) -> dict:
    node = knowledge_repository.upsert_node(workspace_id, user_id, "club_principle", "club_intelligence", "club_principle", str(principle["id"]), {
        "title": principle["title"], "summary": principle["description"], "tactical_topic": principle["principle_area"], "reliability_level": "alta" if principle["validation_state"] == "staff_validated" else "media",
        "validation_state": principle["validation_state"], "nature": principle["source_kind"], "metadata": {"club_id": principle["club_id"], "team_ids": principle.get("team_ids_json") or []}, "tags": [principle["principle_area"], "club_principle"],
    })
    knowledge_repository.upsert_edge(workspace_id, node, club_node, "declared_by_club", "club_principle", str(principle["id"]), "Principio tecnico dichiarato dal club.", "alta", principle["validation_state"], {})
    return node


def publish_snapshot(workspace_id: int, user_id: int, club_node: dict, snapshot: dict) -> dict:
    node = knowledge_repository.upsert_node(workspace_id, user_id, "club_intelligence_snapshot", "club_intelligence", "club_snapshot", str(snapshot["id"]), {
        "title": "Sintesi Club Intelligence", "summary": "Sintesi prudente di continuita e differenze tra i contesti autorizzati.", "reliability_level": "media", "validation_state": "staff_review_required", "nature": "dato_derivato",
        "metadata": {"club_id": snapshot["club_id"], "team_ids": snapshot.get("team_ids_json") or [], "limitations": snapshot.get("limitations_json") or []}, "tags": ["club", "snapshot"],
    })
    knowledge_repository.upsert_edge(workspace_id, node, club_node, "summarizes", "club_snapshot", str(snapshot["id"]), "Sintesi del contesto tecnico autorizzato del club.", "media", "staff_review_required", {})
    return node
