from fastapi import APIRouter, Depends, HTTPException, status

from app.models.knowledge import (
    CoachProfileUpdate,
    DeleteKnowledgeItemResponse,
    KnowledgeEnvelope,
    RosterPlayer,
    RosterPlayerCreate,
    RosterPlayerUpdate,
    TeamProfileUpdate,
)
from app.services import knowledge_service
from usage_guard import require_user


router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


def _user_id(user: dict) -> int:
    return int(user["id"])


@router.post("", response_model=KnowledgeEnvelope, status_code=status.HTTP_201_CREATED)
def create_knowledge_foundation(user=Depends(require_user)):
    return KnowledgeEnvelope(knowledge=knowledge_service.get_knowledge(_user_id(user)))


@router.get("", response_model=KnowledgeEnvelope)
def load_knowledge(user=Depends(require_user)):
    return KnowledgeEnvelope(knowledge=knowledge_service.get_knowledge(_user_id(user)))


@router.put("/coach-profile", response_model=KnowledgeEnvelope)
def save_coach_profile(payload: CoachProfileUpdate, user=Depends(require_user)):
    knowledge = knowledge_service.update_coach_profile(_user_id(user), payload)
    return KnowledgeEnvelope(knowledge=knowledge)


@router.put("/team-profile", response_model=KnowledgeEnvelope)
def save_team_profile(payload: TeamProfileUpdate, user=Depends(require_user)):
    knowledge = knowledge_service.update_team_profile(_user_id(user), payload)
    return KnowledgeEnvelope(knowledge=knowledge)


@router.post("/roster", response_model=RosterPlayer, status_code=status.HTTP_201_CREATED)
def create_roster_player(payload: RosterPlayerCreate, user=Depends(require_user)):
    return knowledge_service.add_roster_player(_user_id(user), payload)


@router.put("/roster/{player_id}", response_model=RosterPlayer)
def update_roster_player(player_id: int, payload: RosterPlayerUpdate, user=Depends(require_user)):
    player = knowledge_service.replace_roster_player(_user_id(user), player_id, payload)
    if not player:
        raise HTTPException(status_code=404, detail="Giocatore Knowledge non trovato")
    return player


@router.delete("/roster/{player_id}", response_model=DeleteKnowledgeItemResponse)
def delete_roster_player(player_id: int, user=Depends(require_user)):
    if not knowledge_service.remove_roster_player(_user_id(user), player_id):
        raise HTTPException(status_code=404, detail="Giocatore Knowledge non trovato")
    return DeleteKnowledgeItemResponse(player_id=player_id)
