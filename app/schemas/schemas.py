from pydantic import BaseModel
from typing import Optional


# ─── Team Schemas ─────────────────────────────────────────────────────────────

class TeamBase(BaseModel):
    """Fields shared between creating and reading a team."""
    name: str
    short_name: Optional[str] = None
    country: Optional[str] = None
    founded: Optional[int] = None
    stadium: Optional[str] = None
    stadium_capacity: Optional[int] = None
    manager: Optional[str] = None


class TeamCreate(TeamBase):
    """
    Schema for POST /teams/ request body.
    Inherits all fields from TeamBase.
    name is required, everything else is optional.
    """
    pass


class TeamUpdate(BaseModel):
    """
    Schema for PATCH /teams/{id} request body.
    All fields are optional - client only sends what they want to change.
    """
    name: Optional[str] = None
    short_name: Optional[str] = None
    country: Optional[str] = None
    founded: Optional[int] = None
    stadium: Optional[str] = None
    stadium_capacity: Optional[int] = None
    manager: Optional[str] = None


class TeamOut(TeamBase):
    """
    Schema for API responses.
    Includes id and external_id which come from the database.
    model_config tells Pydantic to read data from SQLAlchemy objects.
    """
    id: int
    external_id: Optional[int] = None

    model_config = {"from_attributes": True}


# ─── Player Schemas ────────────────────────────────────────────────────────────

class PlayerBase(BaseModel):
    name: str
    team_id: Optional[int] = None
    position: Optional[str] = None
    nationality: Optional[str] = None
    age: Optional[int] = None
    shirt_number: Optional[int] = None
    market_value_eur: Optional[float] = None


class PlayerCreate(PlayerBase):
    pass


class PlayerUpdate(BaseModel):
    name: Optional[str] = None
    team_id: Optional[int] = None
    position: Optional[str] = None
    nationality: Optional[str] = None
    age: Optional[int] = None
    shirt_number: Optional[int] = None
    market_value_eur: Optional[float] = None


class PlayerOut(PlayerBase):
    id: int
    external_id: Optional[int] = None
    model_config = {"from_attributes": True}


# ─── Match Schemas ─────────────────────────────────────────────────────────────

from datetime import date

class MatchBase(BaseModel):
    home_team_id: int
    away_team_id: int
    match_date: date
    competition: Optional[str] = None
    season: Optional[str] = None
    matchday: Optional[int] = None
    home_goals: Optional[int] = None
    away_goals: Optional[int] = None
    status: Optional[str] = "SCHEDULED"


class MatchCreate(MatchBase):
    pass


class MatchUpdate(BaseModel):
    match_date: Optional[date] = None
    competition: Optional[str] = None
    season: Optional[str] = None
    matchday: Optional[int] = None
    home_goals: Optional[int] = None
    away_goals: Optional[int] = None
    status: Optional[str] = None


class MatchOut(MatchBase):
    id: int
    home_team_name: Optional[str] = None
    away_team_name: Optional[str] = None
    model_config = {"from_attributes": True}
