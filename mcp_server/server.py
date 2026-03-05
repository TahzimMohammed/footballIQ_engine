"""
MCP (Model Context Protocol) Server for FootballIQ.

This exposes our API as tools that AI assistants can use.
When Claude asks "How is Liverpool performing?", it can call
the get_team_form tool and get a structured answer back.

Run this separately from the main API:
  python mcp_server/server.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastmcp import FastMCP
from app.database import SessionLocal
from app.services.analytics import get_team_form, get_leaderboard, get_head_to_head
from app.ml.predictor import predict_match
from app.models.models import Team, Player, Match

# Create the MCP server
# The name and description help AI assistants understand what this server does
mcp = FastMCP(
    name="FootballIQ",
    instructions="Football analytics server. Use these tools to get team form, leaderboards, predictions and head-to-head records from real European football data (2008-2016)."
)


@mcp.tool()
def search_team(name: str) -> dict:
    """
    Search for a team by name. Returns team ID and details.
    Use this first to find the team_id before calling other tools.
    
    Args:
        name: Team name or partial name e.g. 'Liverpool', 'Arsenal', 'Barcelona'
    """
    db = SessionLocal()
    try:
        teams = db.query(Team).filter(
            Team.name.ilike(f"%{name}%")
        ).limit(5).all()

        if not teams:
            return {"error": f"No teams found matching '{name}'"}

        return {
            "teams": [
                {
                    "id": t.id,
                    "name": t.name,
                    "short_name": t.short_name,
                    "country": t.country
                } for t in teams
            ]
        }
    finally:
        db.close()


@mcp.tool()
def get_form(team_id: int, n: int = 5) -> dict:
    """
    Get a team's recent form - last N match results with points and goal difference.
    
    Args:
        team_id: The team's ID (get this from search_team first)
        n: Number of recent matches to include (default 5, max 20)
    """
    db = SessionLocal()
    try:
        result = get_team_form(db, team_id, n)
        if not result:
            return {"error": f"Team {team_id} not found"}
        return result
    finally:
        db.close()


@mcp.tool()
def get_standings(competition: str, season: str) -> dict:
    """
    Get the league table for a competition and season.
    
    Args:
        competition: League name e.g. 'Premier League', 'La Liga', 'Bundesliga'
        season: Season in format 'YYYY/YYYY' e.g. '2015/2016'
    """
    db = SessionLocal()
    try:
        table = get_leaderboard(db, competition, season)
        if not table:
            return {"error": f"No data found for {competition} {season}"}
        return {
            "competition": competition,
            "season": season,
            "table": table[:10]  # Top 10 only to keep response concise
        }
    finally:
        db.close()


@mcp.tool()
def predict_outcome(home_team_id: int, away_team_id: int) -> dict:
    """
    Predict the outcome of a match using the Random Forest ML model.
    Returns win/draw/loss probabilities.
    
    Args:
        home_team_id: ID of the home team
        away_team_id: ID of the away team
    """
    db = SessionLocal()
    try:
        result = predict_match(db, home_team_id, away_team_id)
        if not result:
            return {"error": "One or both teams not found"}
        return result
    finally:
        db.close()


@mcp.tool()
def head_to_head(team1_id: int, team2_id: int) -> dict:
    """
    Get the full head-to-head record between two teams.
    
    Args:
        team1_id: First team ID
        team2_id: Second team ID
    """
    db = SessionLocal()
    try:
        result = get_head_to_head(db, team1_id, team2_id)
        if not result:
            return {"error": "One or both teams not found"}
        return result
    finally:
        db.close()


@mcp.tool()
def list_teams(country: str = None, limit: int = 20) -> dict:
    """
    List all teams, optionally filtered by country.
    
    Args:
        country: Country name to filter by e.g. 'England', 'Spain', 'Germany'
        limit: Maximum number of teams to return
    """
    db = SessionLocal()
    try:
        query = db.query(Team)
        if country:
            query = query.filter(Team.country.ilike(f"%{country}%"))
        teams = query.limit(limit).all()
        return {
            "teams": [
                {"id": t.id, "name": t.name, "country": t.country}
                for t in teams
            ]
        }
    finally:
        db.close()


@mcp.tool()
def get_team_players(team_id: int) -> dict:
    """
    Get all players for a team.
    
    Args:
        team_id: The team's ID
    """
    db = SessionLocal()
    try:
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            return {"error": f"Team {team_id} not found"}

        players = db.query(Player).filter(
            Player.team_id == team_id
        ).limit(30).all()

        return {
            "team": team.name,
            "player_count": len(players),
            "players": [
                {
                    "id": p.id,
                    "name": p.name,
                    "position": p.position,
                    "age": p.age,
                    "nationality": p.nationality
                } for p in players
            ]
        }
    finally:
        db.close()


if __name__ == "__main__":
    print("Starting FootballIQ MCP Server...")
    print("Tools available:")
    print("  - search_team")
    print("  - get_form")
    print("  - get_standings")
    print("  - predict_outcome")
    print("  - head_to_head")
    print("  - list_teams")
    print("  - get_team_players")
    mcp.run()
