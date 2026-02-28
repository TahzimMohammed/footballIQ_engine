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
