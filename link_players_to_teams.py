"""
Extract player-team assignments from Kaggle match lineup data.
Logic: assign each player to the team they appeared for most often.
"""
import sqlite3
from collections import defaultdict
from app.database import SessionLocal
from app.models.models import Player, Team

KAGGLE_DB = "data/database.sqlite"

def main():
    kaggle = sqlite3.connect(KAGGLE_DB)
    cursor = kaggle.cursor()

    # Get all 22 player columns from every match
    player_cols = (
        [f"home_player_{i}" for i in range(1, 12)] +
        [f"away_player_{i}" for i in range(1, 12)]
    )
    team_cols = ["home_team_api_id"] * 11 + ["away_team_api_id"] * 11

    cols = ", ".join([f"home_team_api_id, away_team_api_id"] + player_cols)
    cursor.execute(f"SELECT {cols} FROM Match WHERE home_player_1 IS NOT NULL")
    rows = cursor.fetchall()

    print(f"Processing {len(rows)} matches with lineup data...")

    # Count how many times each player appeared for each team
    # player_api_id -> {team_api_id -> count}
    player_team_counts = defaultdict(lambda: defaultdict(int))

    for row in rows:
        home_team_api = row[0]
        away_team_api = row[1]
        players = row[2:]  # all 22 player columns

        for i, player_api_id in enumerate(players):
            if player_api_id is None:
                continue
            team_api_id = home_team_api if i < 11 else away_team_api
            player_team_counts[player_api_id][team_api_id] += 1

    kaggle.close()
    print(f"Found {len(player_team_counts)} players with team data")

    # Now update our database
    db = SessionLocal()

    # Build a mapping from kaggle team_api_id to our team id
    teams = db.query(Team).all()
    kaggle_to_our_team = {t.external_id: t.id for t in teams if t.external_id}

    updated = 0
    not_found = 0

    for player_api_id, team_counts in player_team_counts.items():
        # Find the team this player appeared for most
        most_common_team_api = max(team_counts, key=team_counts.get)
        our_team_id = kaggle_to_our_team.get(most_common_team_api)

        if not our_team_id:
            not_found += 1
            continue

        # Find the player in our database
        player = db.query(Player).filter(
            Player.external_id == player_api_id
        ).first()

        if player:
            player.team_id = our_team_id
            updated += 1

    db.commit()
    print(f"Updated {updated} players with team assignments")
    print(f"Could not find team for {not_found} players")

    # Verify
    with_team = db.query(Player).filter(Player.team_id != None).count()
    print(f"Players with team_id: {with_team}")
    db.close()

if __name__ == "__main__":
    main()
