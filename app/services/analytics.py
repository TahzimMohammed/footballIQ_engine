"""
Analytics service - all the computation logic lives here, separate from the router.
This is the "business logic layer" - routers just handle HTTP, this handles the maths.
"""
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from app.models.models import Match, Team
from typing import Optional


def get_team_form(db: Session, team_id: int, n: int = 5) -> dict:
    """
    Get a team's last N matches and compute their form.
    
    Form is calculated as:
    - Win = 3 points
    - Draw = 1 point  
    - Loss = 0 points
    """
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        return None

    # Get last N finished matches for this team (home or away)
    matches = db.query(Match).filter(
        Match.status == "FINISHED",
        or_(
            Match.home_team_id == team_id,
            Match.away_team_id == team_id
        )
    ).order_by(Match.match_date.desc()).limit(n).all()

    results = []
    points = 0
    wins = draws = losses = goals_for = goals_against = 0

    for match in matches:
        is_home = match.home_team_id == team_id

        if is_home:
            gf = match.home_goals or 0
            ga = match.away_goals or 0
            opponent_id = match.away_team_id
        else:
            gf = match.away_goals or 0
            ga = match.home_goals or 0
            opponent_id = match.home_team_id

        opponent = db.query(Team).filter(Team.id == opponent_id).first()

        if gf > ga:
            result = "W"
            points += 3
            wins += 1
        elif gf == ga:
            result = "D"
            points += 1
            draws += 1
        else:
            result = "L"
            losses += 1

        goals_for += gf
        goals_against += ga

        results.append({
            "match_id": match.id,
            "date": str(match.match_date),
            "opponent": opponent.name if opponent else "Unknown",
            "home_or_away": "H" if is_home else "A",
            "score": f"{gf}-{ga}",
            "result": result,
            "competition": match.competition,
            "season": match.season
        })

    return {
        "team_id": team_id,
        "team_name": team.name,
        "matches_played": len(matches),
        "form_string": "".join([r["result"] for r in results]),
        "points": points,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "goal_difference": goals_for - goals_against,
        "recent_matches": results
    }


def get_leaderboard(db: Session, competition: str, season: str) -> list:
    """
    Compute a league table for a given competition and season.
    
    We go through every match and award points to each team,
    then sort by: points -> goal difference -> goals scored.
    This is exactly how real football tables are calculated.
    """
    matches = db.query(Match).filter(
        Match.competition.ilike(f"%{competition}%"),
        Match.season == season,
        Match.status == "FINISHED"
    ).all()

    # Build a standings dictionary keyed by team_id
    standings = {}

    for match in matches:
        # Initialise both teams if not seen before
        for team_id in [match.home_team_id, match.away_team_id]:
            if team_id not in standings:
                team = db.query(Team).filter(Team.id == team_id).first()
                standings[team_id] = {
                    "team_id": team_id,
                    "team_name": team.name if team else "Unknown",
                    "played": 0, "wins": 0, "draws": 0, "losses": 0,
                    "goals_for": 0, "goals_against": 0,
                    "goal_difference": 0, "points": 0
                }

        hg = match.home_goals or 0
        ag = match.away_goals or 0

        # Update home team stats
        standings[match.home_team_id]["played"] += 1
        standings[match.home_team_id]["goals_for"] += hg
        standings[match.home_team_id]["goals_against"] += ag

        # Update away team stats
        standings[match.away_team_id]["played"] += 1
        standings[match.away_team_id]["goals_for"] += ag
        standings[match.away_team_id]["goals_against"] += hg

        # Award points
        if hg > ag:
            standings[match.home_team_id]["wins"] += 1
            standings[match.home_team_id]["points"] += 3
            standings[match.away_team_id]["losses"] += 1
        elif hg == ag:
            standings[match.home_team_id]["draws"] += 1
            standings[match.home_team_id]["points"] += 1
            standings[match.away_team_id]["draws"] += 1
            standings[match.away_team_id]["points"] += 1
        else:
            standings[match.away_team_id]["wins"] += 1
            standings[match.away_team_id]["points"] += 3
            standings[match.home_team_id]["losses"] += 1

    # Calculate goal difference for each team
    for team_id in standings:
        s = standings[team_id]
        s["goal_difference"] = s["goals_for"] - s["goals_against"]

    # Sort: points desc, then goal difference desc, then goals for desc
    sorted_standings = sorted(
        standings.values(),
        key=lambda x: (x["points"], x["goal_difference"], x["goals_for"]),
        reverse=True
    )

    # Add position numbers
    for i, team in enumerate(sorted_standings):
        team["position"] = i + 1

    return sorted_standings


def get_head_to_head(db: Session, team1_id: int, team2_id: int) -> dict:
    """
    Get the full head-to-head record between two teams.
    """
    team1 = db.query(Team).filter(Team.id == team1_id).first()
    team2 = db.query(Team).filter(Team.id == team2_id).first()

    if not team1 or not team2:
        return None

    matches = db.query(Match).filter(
        Match.status == "FINISHED",
        or_(
            and_(Match.home_team_id == team1_id, Match.away_team_id == team2_id),
            and_(Match.home_team_id == team2_id, Match.away_team_id == team1_id)
        )
    ).order_by(Match.match_date.desc()).all()

    team1_wins = team2_wins = draws = 0
    team1_goals = team2_goals = 0
    results = []

    for match in matches:
        hg = match.home_goals or 0
        ag = match.away_goals or 0

        if match.home_team_id == team1_id:
            t1g, t2g = hg, ag
        else:
            t1g, t2g = ag, hg

        team1_goals += t1g
        team2_goals += t2g

        if t1g > t2g:
            winner = team1.name
            team1_wins += 1
        elif t2g > t1g:
            winner = team2.name
            team2_wins += 1
        else:
            winner = "Draw"
            draws += 1

        results.append({
            "date": str(match.match_date),
            "home_team": team1.name if match.home_team_id == team1_id else team2.name,
            "away_team": team2.name if match.home_team_id == team1_id else team1.name,
            "score": f"{hg}-{ag}",
            "winner": winner,
            "competition": match.competition,
            "season": match.season
        })

    return {
        "team1": team1.name,
        "team2": team2.name,
        "total_matches": len(matches),
        f"{team1.name}_wins": team1_wins,
        f"{team2.name}_wins": team2_wins,
        "draws": draws,
        f"{team1.name}_goals": team1_goals,
        f"{team2.name}_goals": team2_goals,
        "matches": results
    }
