from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.models import Player, Team, User
from app.schemas.schemas import PlayerCreate, PlayerUpdate, PlayerOut
from app.services.auth import get_current_user, get_admin_user

router = APIRouter(prefix="/players", tags=["Players"])


@router.get("/", response_model=List[PlayerOut])
def list_players(
    skip: int = Query(0),
    limit: int = Query(20),
    team_id: Optional[int] = Query(None, description="Filter by team ID"),
    position: Optional[str] = Query(None, description="Filter by position e.g. GK, DEF, MID, FWD"),
    db: Session = Depends(get_db)
):
    query = db.query(Player)
    if team_id:
        query = query.filter(Player.team_id == team_id)
    if position:
        query = query.filter(Player.position.ilike(f"%{position}%"))
    return query.offset(skip).limit(limit).all()


@router.get("/{player_id}", response_model=PlayerOut)
def get_player(player_id: int, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail=f"Player {player_id} not found")
    return player


@router.post("/", response_model=PlayerOut, status_code=201)
def create_player(
    player_in: PlayerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Validate team exists if team_id is provided
    if player_in.team_id:
        team = db.query(Team).filter(Team.id == player_in.team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail=f"Team {player_in.team_id} not found")

    player = Player(**player_in.model_dump())
    db.add(player)
    db.commit()
    db.refresh(player)
    return player


@router.patch("/{player_id}", response_model=PlayerOut)
def update_player(
    player_id: int,
    player_in: PlayerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail=f"Player {player_id} not found")

    for field, value in player_in.model_dump(exclude_unset=True).items():
        setattr(player, field, value)

    db.commit()
    db.refresh(player)
    return player


@router.delete("/{player_id}", status_code=204)
def delete_player(
    player_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail=f"Player {player_id} not found")
    db.delete(player)
    db.commit()
