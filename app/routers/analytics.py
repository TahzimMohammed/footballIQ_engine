from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.analytics import get_team_form, get_leaderboard, get_head_to_head

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/form/{team_id}")
def team_form(
    team_id: int,
    n: int = Query(5, description="Number of recent matches to include", ge=1, le=20),
    db: Session = Depends(get_db)
):
    """
    Get a team's recent form — last N results with points and goal difference.
    ge=1, le=20 means FastAPI will reject values outside 1-20 automatically.
    """
    result = get_team_form(db, team_id, n)
    if not result:
        raise HTTPException(status_code=404, detail=f"Team {team_id} not found")
    return result


@router.get("/leaderboard")
def leaderboard(
    competition: str = Query(..., description="Competition name e.g. 'Premier League'"),
    season: str = Query(..., description="Season e.g. '2008/2009'"),
    db: Session = Depends(get_db)
):
    """
    Get the full league table for a competition and season.
    The ... means this parameter is REQUIRED (no default value).
    """
    table = get_leaderboard(db, competition, season)
    if not table:
        raise HTTPException(status_code=404, detail="No matches found for this competition and season")
    return {"competition": competition, "season": season, "table": table}


@router.get("/head-to-head")
def head_to_head(
    team1_id: int = Query(..., description="First team ID"),
    team2_id: int = Query(..., description="Second team ID"),
    db: Session = Depends(get_db)
):
    """Get the full head-to-head record between two teams."""
    if team1_id == team2_id:
        raise HTTPException(status_code=400, detail="team1_id and team2_id must be different")
    result = get_head_to_head(db, team1_id, team2_id)
    if not result:
        raise HTTPException(status_code=404, detail="One or both teams not found")
    if result["total_matches"] == 0:
        raise HTTPException(status_code=404, detail="No matches found between these teams")
    return result
