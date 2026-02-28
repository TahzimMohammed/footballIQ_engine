from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.models import Team, User
from app.schemas.schemas import TeamCreate, TeamUpdate, TeamOut
from app.services.auth import get_current_user, get_admin_user

router = APIRouter(prefix="/teams", tags=["Teams"])


@router.get("/", response_model=List[TeamOut])
def list_teams(
    skip: int = Query(0, description="How many records to skip - used for pagination"),
    limit: int = Query(20, description="Maximum number of teams to return"),
    country: Optional[str] = Query(None, description="Filter by country name"),
    db: Session = Depends(get_db)
):
    """
    Get a list of teams.
    - Use skip and limit for pagination e.g. skip=20&limit=20 gets page 2
    - Use country to filter e.g. country=England
    """
    query = db.query(Team)
    if country:
        query = query.filter(Team.country.ilike(f"%{country}%"))
    return query.offset(skip).limit(limit).all()


@router.get("/{team_id}", response_model=TeamOut)
def get_team(team_id: int, db: Session = Depends(get_db)):
    """Get a single team by its ID."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail=f"Team {team_id} not found")
    return team


@router.post("/", response_model=TeamOut, status_code=201)
def create_team(
    team_in: TeamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new team.
    Requires authentication - send Bearer token in Authorization header.
    """
    if db.query(Team).filter(Team.name == team_in.name).first():
        raise HTTPException(status_code=400, detail="A team with this name already exists")
    team = Team(**team_in.model_dump())
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


@router.patch("/{team_id}", response_model=TeamOut)
def update_team(
    team_id: int,
    team_in: TeamUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Partially update a team.
    Only send the fields you want to change.
    Requires authentication.
    """
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail=f"Team {team_id} not found")

    # model_dump(exclude_unset=True) only returns fields the client actually sent
    # This is what makes PATCH work - we don't overwrite fields that weren't sent
    for field, value in team_in.model_dump(exclude_unset=True).items():
        setattr(team, field, value)

    db.commit()
    db.refresh(team)
    return team


@router.delete("/{team_id}", status_code=204)
def delete_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    Delete a team.
    Requires ADMIN privileges.
    Returns 204 No Content on success (no response body needed).
    """
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail=f"Team {team_id} not found")
    db.delete(team)
    db.commit()
