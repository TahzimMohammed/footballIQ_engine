from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.models import Match, Team, User
from app.schemas.schemas import MatchCreate, MatchUpdate, MatchOut
from app.services.auth import get_current_user, get_admin_user

router = APIRouter(prefix="/matches", tags=["Matches"])


@router.get("/", response_model=List[MatchOut])
def list_matches(
    skip: int = Query(0),
    limit: int = Query(20),
    season: Optional[str] = Query(None, description="Filter by season e.g. 2008/2009"),
    competition: Optional[str] = Query(None, description="Filter by competition name"),
    status: Optional[str] = Query(None, description="Filter by status: SCHEDULED, FINISHED"),
    db: Session = Depends(get_db)
):
    query = db.query(Match)
    if season:
        query = query.filter(Match.season == season)
    if competition:
        query = query.filter(Match.competition.ilike(f"%{competition}%"))
    if status:
        query = query.filter(Match.status == status)
    return query.offset(skip).limit(limit).all()


@router.get("/{match_id}", response_model=MatchOut)
def get_match(match_id: int, db: Session = Depends(get_db)):
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found")
    return match


@router.post("/", response_model=MatchOut, status_code=201)
def create_match(
    match_in: MatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # A team cannot play against itself
    if match_in.home_team_id == match_in.away_team_id:
        raise HTTPException(status_code=400, detail="Home and away teams must be different")

    # Validate both teams exist
    for team_id in [match_in.home_team_id, match_in.away_team_id]:
        if not db.query(Team).filter(Team.id == team_id).first():
            raise HTTPException(status_code=404, detail=f"Team {team_id} not found")

    match = Match(**match_in.model_dump())
    db.add(match)
    db.commit()
    db.refresh(match)
    return match


@router.patch("/{match_id}", response_model=MatchOut)
def update_match(
    match_id: int,
    match_in: MatchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found")

    for field, value in match_in.model_dump(exclude_unset=True).items():
        setattr(match, field, value)

    db.commit()
    db.refresh(match)
    return match


@router.delete("/{match_id}", status_code=204)
def delete_match(
    match_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found")
    db.delete(match)
    db.commit()
