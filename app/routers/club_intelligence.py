from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.models.club_intelligence import ClubCreate, ClubEnvelope, ClubMemberCreate, ClubMemberUpdate, ClubPrincipleCreate, ClubResourceCreate, ClubSnapshotRequest, ClubTeamCreate, ClubTeamUpdate, ClubUpdate
from app.services import club_intelligence_service as service
from usage_guard import require_user


router = APIRouter(prefix="/api/club-intelligence", tags=["club-intelligence"])


def _uid(user: dict) -> int: return int(user["id"])


def _call(func, *args):
    try: return ClubEnvelope(data=func(*args))
    except PermissionError as exc: raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/clubs", response_model=ClubEnvelope, status_code=status.HTTP_201_CREATED)
def create_club(payload: ClubCreate, user=Depends(require_user)): return _call(service.create, _uid(user), payload.model_dump())

@router.get("/clubs", response_model=ClubEnvelope)
def list_clubs(user=Depends(require_user)): return _call(service.list_for_user, _uid(user))

@router.get("/clubs/{club_id}", response_model=ClubEnvelope)
def get_club(club_id: int, user=Depends(require_user)): return _call(service.detail, club_id, _uid(user))

@router.patch("/clubs/{club_id}", response_model=ClubEnvelope)
def update_club(club_id: int, payload: ClubUpdate, user=Depends(require_user)): return _call(service.update_club, club_id, _uid(user), payload.model_dump(exclude_unset=True))

@router.get("/clubs/{club_id}/members", response_model=ClubEnvelope)
def list_members(club_id: int, user=Depends(require_user)): return _call(service.members, club_id, _uid(user))

@router.post("/clubs/{club_id}/members", response_model=ClubEnvelope, status_code=201)
def add_member(club_id: int, payload: ClubMemberCreate, user=Depends(require_user)): return _call(service.add_member, club_id, _uid(user), payload.model_dump())

@router.patch("/clubs/{club_id}/members/{membership_id}", response_model=ClubEnvelope)
def update_member(club_id: int, membership_id: int, payload: ClubMemberUpdate, user=Depends(require_user)): return _call(service.change_member, club_id, membership_id, _uid(user), payload.model_dump(exclude_unset=True))

@router.get("/clubs/{club_id}/teams", response_model=ClubEnvelope)
def list_teams(club_id: int, user=Depends(require_user)): return _call(service.teams, club_id, _uid(user))

@router.post("/clubs/{club_id}/teams", response_model=ClubEnvelope, status_code=201)
def add_team(club_id: int, payload: ClubTeamCreate, user=Depends(require_user)): return _call(service.add_team, club_id, _uid(user), payload.model_dump())

@router.patch("/clubs/{club_id}/teams/{team_id}", response_model=ClubEnvelope)
def update_team(club_id: int, team_id: int, payload: ClubTeamUpdate, user=Depends(require_user)): return _call(service.change_team, club_id, team_id, _uid(user), payload.model_dump(exclude_unset=True))

@router.get("/clubs/{club_id}/principles", response_model=ClubEnvelope)
def list_principles(club_id: int, user=Depends(require_user)): return _call(service.principles, club_id, _uid(user))

@router.post("/clubs/{club_id}/principles", response_model=ClubEnvelope, status_code=201)
def add_principle(club_id: int, payload: ClubPrincipleCreate, user=Depends(require_user)): return _call(service.add_principle, club_id, _uid(user), payload.model_dump())

@router.get("/clubs/{club_id}/resources", response_model=ClubEnvelope)
def list_resources(club_id: int, user=Depends(require_user)): return _call(service.resources, club_id, _uid(user))

@router.post("/clubs/{club_id}/resources", response_model=ClubEnvelope, status_code=201)
def share_resource(club_id: int, payload: ClubResourceCreate, user=Depends(require_user)): return _call(service.share_resource, club_id, _uid(user), payload.model_dump())

@router.get("/clubs/{club_id}/overview", response_model=ClubEnvelope)
def get_overview(club_id: int, team_ids: str = Query(default=""), user=Depends(require_user)):
    parsed = [int(value) for value in team_ids.split(",") if value.strip().isdigit()]
    return _call(service.overview, club_id, _uid(user), parsed)

@router.post("/clubs/{club_id}/snapshots", response_model=ClubEnvelope, status_code=201)
def create_snapshot(club_id: int, payload: ClubSnapshotRequest, user=Depends(require_user)): return _call(service.snapshot, club_id, _uid(user), payload.team_ids, payload.period_label)
