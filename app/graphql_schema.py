"""
GraphQL schema using Strawberry.

Strawberry uses Python type hints and decorators to define the schema.
No separate schema.graphql file needed - the schema is generated from 
the Python classes automatically, just like FastAPI generates OpenAPI docs.

Three decorators to know:
  @strawberry.type    = a GraphQL object type (like a class/model)
  @strawberry.field   = a field that can be queried
  @strawberry.type + Query class = the root query (entry point)
"""
import strawberry
from strawberry.fastapi import GraphQLRouter
from typing import List, Optional
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.models import Team as TeamModel, Player as PlayerModel, Match as MatchModel


def get_db():
    """Get a database session for GraphQL resolvers."""
    return SessionLocal()


# ─── GraphQL Types ─────────────────────────────────────────────────────────────
# These are like Pydantic schemas but for GraphQL
# Each field here becomes queryable in GraphQL

@strawberry.type
class PlayerType:
    """Represents a player in GraphQL."""
    id: int
    name: str
    position: Optional[str]
    nationality: Optional[str]
    age: Optional[int]
    team_id: Optional[int]


@strawberry.type
class MatchType:
    """Represents a match in GraphQL."""
    id: int
    home_team_id: int
    away_team_id: int
    match_date: str        # GraphQL doesn't have a Date type, so we use str
    competition: Optional[str]
    season: Optional[str]
    home_goals: Optional[int]
    away_goals: Optional[int]
    status: str


@strawberry.type
class TeamType:
    """
    Represents a team in GraphQL.
    
    Notice players and matches are computed fields (resolvers).
    They only run the database query IF the client asked for them.
    This is lazy loading - no wasted queries.
    """
    id: int
    name: str
    short_name: Optional[str]
    country: Optional[str]
    stadium: Optional[str]

    @strawberry.field
    def players(self) -> List[PlayerType]:
        """
        Resolver - runs only when client requests players.
        self.id refers to the team's id.
        """
        db = get_db()
        try:
            players = db.query(PlayerModel).filter(
                PlayerModel.team_id == self.id
            ).limit(50).all()
            return [
                PlayerType(
                    id=p.id,
                    name=p.name,
                    position=p.position,
                    nationality=p.nationality,
                    age=p.age,
                    team_id=p.team_id
                ) for p in players
            ]
        finally:
            db.close()

    @strawberry.field
    def recent_matches(self, limit: int = 5) -> List[MatchType]:
        """
        Resolver for recent matches.
        Note: limit is a parameter the client can pass in the query.
        """
        from sqlalchemy import or_
        db = get_db()
        try:
            matches = db.query(MatchModel).filter(
                MatchModel.status == "FINISHED",
                or_(
                    MatchModel.home_team_id == self.id,
                    MatchModel.away_team_id == self.id
                )
            ).order_by(MatchModel.match_date.desc()).limit(limit).all()
            return [
                MatchType(
                    id=m.id,
                    home_team_id=m.home_team_id,
                    away_team_id=m.away_team_id,
                    match_date=str(m.match_date),
                    competition=m.competition,
                    season=m.season,
                    home_goals=m.home_goals,
                    away_goals=m.away_goals,
                    status=m.status
                ) for m in matches
            ]
        finally:
            db.close()


# ─── Root Query ────────────────────────────────────────────────────────────────
# This is the entry point - all GraphQL queries start here

@strawberry.type
class Query:

    @strawberry.field
    def teams(self, limit: int = 10, country: Optional[str] = None) -> List[TeamType]:
        """
        Query all teams.
        Example GraphQL query:
          { teams(limit: 5) { id name country } }
        """
        db = get_db()
        try:
            query = db.query(TeamModel)
            if country:
                query = query.filter(TeamModel.country.ilike(f"%{country}%"))
            teams = query.limit(limit).all()
            return [
                TeamType(
                    id=t.id,
                    name=t.name,
                    short_name=t.short_name,
                    country=t.country,
                    stadium=t.stadium
                ) for t in teams
            ]
        finally:
            db.close()

    @strawberry.field
    def team(self, id: int) -> Optional[TeamType]:
        """
        Query a single team by ID.
        Example:
          { team(id: 30) { name players { name age } } }
        """
        db = get_db()
        try:
            t = db.query(TeamModel).filter(TeamModel.id == id).first()
            if not t:
                return None
            return TeamType(
                id=t.id,
                name=t.name,
                short_name=t.short_name,
                country=t.country,
                stadium=t.stadium
            )
        finally:
            db.close()

    @strawberry.field
    def matches(
        self,
        season: Optional[str] = None,
        competition: Optional[str] = None,
        limit: int = 10
    ) -> List[MatchType]:
        """
        Query matches with optional filters.
        Example:
          { matches(season: "2008/2009", limit: 5) { home_team_id away_team_id home_goals away_goals } }
        """
        db = get_db()
        try:
            query = db.query(MatchModel).filter(MatchModel.status == "FINISHED")
            if season:
                query = query.filter(MatchModel.season == season)
            if competition:
                query = query.filter(MatchModel.competition.ilike(f"%{competition}%"))
            matches = query.limit(limit).all()
            return [
                MatchType(
                    id=m.id,
                    home_team_id=m.home_team_id,
                    away_team_id=m.away_team_id,
                    match_date=str(m.match_date),
                    competition=m.competition,
                    season=m.season,
                    home_goals=m.home_goals,
                    away_goals=m.away_goals,
                    status=m.status
                ) for m in matches
            ]
        finally:
            db.close()


# Create the schema and router
schema = strawberry.Schema(query=Query)
graphql_router = GraphQLRouter(schema, graphiql=True)
