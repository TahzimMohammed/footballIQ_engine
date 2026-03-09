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


def get_team_dna(db: Session, team_id: int) -> dict:
    """
    Compute a team's DNA fingerprint from their full match history.

    6 dimensions computed:
    - attack_intensity: How aggressively they score (goals per game)
    - defensive_solidity: How well they keep clean sheets
    - consistency: How predictable their results are (low variance = consistent)
    - comeback_ability: How often they win/draw after going behind
    - big_game_performance: Performance vs top-half teams vs bottom-half
    - home_fortress: How much stronger they are at home vs away
    """
    from sqlalchemy import or_, and_
    import statistics

    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        return None

    # Get ALL finished matches for this team
    all_matches = db.query(Match).filter(
        Match.status == "FINISHED",
        or_(
            Match.home_team_id == team_id,
            Match.away_team_id == team_id
        )
    ).order_by(Match.match_date.asc()).all()

    if len(all_matches) < 10:
        return {"error": "Not enough match data for DNA analysis (minimum 10 matches)"}

    # ── Raw stats collection ──────────────────────────────────────────────────
    goals_scored_list = []
    goals_conceded_list = []
    points_list = []
    home_points = []
    away_points = []
    comeback_attempts = 0
    comeback_successes = 0
    results_vs_strong = []  # vs teams with good overall record
    results_vs_weak = []

    for match in all_matches:
        is_home = match.home_team_id == team_id
        gf = (match.home_goals if is_home else match.away_goals) or 0
        ga = (match.away_goals if is_home else match.home_goals) or 0

        goals_scored_list.append(gf)
        goals_conceded_list.append(ga)

        if gf > ga:
            pts = 3
        elif gf == ga:
            pts = 1
        else:
            pts = 0

        points_list.append(pts)

        if is_home:
            home_points.append(pts)
        else:
            away_points.append(pts)

    # ── 1. Attack Intensity (0-1) ─────────────────────────────────────────────
    avg_goals_scored = sum(goals_scored_list) / len(goals_scored_list)
    # Normalise: 0 goals = 0.0, 3+ goals per game = 1.0
    attack_intensity = min(avg_goals_scored / 3.0, 1.0)

    # ── 2. Defensive Solidity (0-1) ───────────────────────────────────────────
    avg_goals_conceded = sum(goals_conceded_list) / len(goals_conceded_list)
    clean_sheets = sum(1 for g in goals_conceded_list if g == 0)
    clean_sheet_rate = clean_sheets / len(goals_conceded_list)
    # Low conceding + high clean sheets = high solidity
    defensive_solidity = (clean_sheet_rate + max(0, 1 - avg_goals_conceded / 3.0)) / 2

    # ── 3. Consistency (0-1) ──────────────────────────────────────────────────
    # Low standard deviation in points = consistent
    if len(points_list) > 1:
        pts_std = statistics.stdev(points_list)
        # Max possible std for 0/1/3 points is around 1.4
        consistency = max(0, 1 - (pts_std / 1.4))
    else:
        consistency = 0.5

    # ── 4. Comeback Ability (0-1) ─────────────────────────────────────────────
    # Look at matches where they conceded first
    for match in all_matches:
        is_home = match.home_team_id == team_id
        gf = (match.home_goals if is_home else match.away_goals) or 0
        ga = (match.away_goals if is_home else match.home_goals) or 0

        # If they conceded more than scored at some point but ended level or won
        # We approximate: if they lost by 1+ goals but final score is draw or win
        # Simple proxy: matches where ga > 0 and they still got points
        if ga > 0:
            comeback_attempts += 1
            if gf >= ga:  # drew or won despite conceding
                comeback_successes += 1

    comeback_ability = comeback_successes / comeback_attempts if comeback_attempts > 0 else 0.5

    # ── 5. Home Fortress (0-1) ────────────────────────────────────────────────
    avg_home_pts = sum(home_points) / len(home_points) if home_points else 1.5
    avg_away_pts = sum(away_points) / len(away_points) if away_points else 1.0
    # How much better are they at home vs away?
    home_advantage = avg_home_pts - avg_away_pts
    # Normalise: 0 difference = 0.5, +3 difference = 1.0, -3 = 0.0
    home_fortress = min(max((home_advantage + 3) / 6, 0), 1)

    # ── 6. Big Game Performance (0-1) ─────────────────────────────────────────
    # Compare points per game vs teams in top half vs bottom half of all teams
    # Get all team win rates to determine "strong" vs "weak" opponents
    all_team_ids = set()
    for m in all_matches:
        all_team_ids.add(m.home_team_id)
        all_team_ids.add(m.away_team_id)

    team_win_rates = {}
    for tid in all_team_ids:
        if tid == team_id:
            continue
        opp_matches = db.query(Match).filter(
            Match.status == "FINISHED",
            or_(Match.home_team_id == tid, Match.away_team_id == tid)
        ).limit(20).all()
        if opp_matches:
            wins = sum(1 for m in opp_matches if
                (m.home_team_id == tid and (m.home_goals or 0) > (m.away_goals or 0)) or
                (m.away_team_id == tid and (m.away_goals or 0) > (m.home_goals or 0))
            )
            team_win_rates[tid] = wins / len(opp_matches)

    if team_win_rates:
        median_win_rate = sorted(team_win_rates.values())[len(team_win_rates) // 2]

        strong_pts = []
        weak_pts = []

        for match in all_matches:
            is_home = match.home_team_id == team_id
            opp_id = match.away_team_id if is_home else match.home_team_id
            gf = (match.home_goals if is_home else match.away_goals) or 0
            ga = (match.away_goals if is_home else match.home_goals) or 0

            pts = 3 if gf > ga else (1 if gf == ga else 0)
            opp_rate = team_win_rates.get(opp_id, median_win_rate)

            if opp_rate >= median_win_rate:
                strong_pts.append(pts)
            else:
                weak_pts.append(pts)

        avg_vs_strong = sum(strong_pts) / len(strong_pts) if strong_pts else 1.0
        avg_vs_weak = sum(weak_pts) / len(weak_pts) if weak_pts else 1.5
        # Normalise big game performance
        big_game = min(avg_vs_strong / 3.0, 1.0)
    else:
        big_game = 0.5

    # ── Style Tag Assignment ───────────────────────────────────────────────────
    dimensions = {
        "attack_intensity": round(attack_intensity, 3),
        "defensive_solidity": round(defensive_solidity, 3),
        "consistency": round(consistency, 3),
        "comeback_ability": round(comeback_ability, 3),
        "home_fortress": round(home_fortress, 3),
        "big_game_performance": round(big_game, 3)
    }

    # Assign primary style based on dominant dimensions
    max_dim = max(dimensions, key=dimensions.get)
    dims_for_weakness = {k: v for k, v in dimensions.items() if k != "consistency"}
    min_dim = min(dims_for_weakness, key=dims_for_weakness.get)

    style_map = {
        "attack_intensity": "Entertainers",
        "defensive_solidity": "Fortress",
        "consistency": "Machine",
        "comeback_ability": "Warriors",
        "home_fortress": "Home Kings",
        "big_game_performance": "Big Game Players"
    }

    weakness_map = {
        "attack_intensity": "Toothless Attack",
        "defensive_solidity": "Leaky Defence",
        "consistency": "Unpredictable",
        "comeback_ability": "No Fight",
        "home_fortress": "No Home Advantage",
        "big_game_performance": "Big Game Bottlers"
    }

    # Overall rating (0-100)
    overall = round(sum(dimensions.values()) / len(dimensions) * 100, 1)

    return {
        "team_id": team_id,
        "team_name": team.name,
        "overall_rating": overall,
        "style": style_map[max_dim],
        "weakness": weakness_map[min_dim],
        "dna": dimensions,
        "summary": {
            "total_matches": len(all_matches),
            "avg_goals_scored": round(avg_goals_scored, 2),
            "avg_goals_conceded": round(avg_goals_conceded, 2),
            "clean_sheet_rate": round(clean_sheet_rate, 2),
            "avg_home_points": round(avg_home_pts, 2),
            "avg_away_points": round(avg_away_pts, 2),
        }
    }
