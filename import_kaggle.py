import sqlite3
from datetime import datetime
from app.database import SessionLocal, engine, Base
from app.models.models import Team, Player, Match

Base.metadata.create_all(bind=engine)

KAGGLE_DB = "data/database.sqlite"


def import_teams(kaggle, session):
    print("Importing teams...")
    cursor = kaggle.cursor()
    cursor.execute("SELECT team_api_id, team_long_name, team_short_name FROM Team")
    rows = cursor.fetchall()

    kaggle_id_to_our_id = {}
    imported = 0

    for api_id, long_name, short_name in rows:
        # Check by external_id OR by name to avoid duplicates
        existing = session.query(Team).filter(
            (Team.external_id == api_id) | (Team.name == long_name)
        ).first()

        if existing:
            kaggle_id_to_our_id[api_id] = existing.id
            continue

        team = Team(
            name=long_name,
            short_name=short_name,
            external_id=api_id
        )
        session.add(team)
        session.flush()
        kaggle_id_to_our_id[api_id] = team.id
        imported += 1

    session.commit()
    print(f"  Done: {imported} teams imported")
    return kaggle_id_to_our_id


def import_players(kaggle, session):
    print("Importing players...")
    cursor = kaggle.cursor()
    cursor.execute("SELECT player_api_id, player_name, birthday FROM Player")
    rows = cursor.fetchall()

    imported = 0
    for api_id, name, birthday in rows:
        existing = session.query(Player).filter(Player.external_id == api_id).first()
        if existing:
            continue

        age = None
        if birthday:
            try:
                age = 2016 - int(birthday[:4])
            except:
                pass

        session.add(Player(name=name, external_id=api_id, age=age))
        imported += 1

    session.commit()
    print(f"  Done: {imported} players imported")


def import_matches(kaggle, session, kaggle_id_to_our_id):
    print("Importing matches (this may take a moment)...")
    cursor = kaggle.cursor()
    cursor.execute("""
        SELECT
            m.match_api_id,
            m.season,
            m.stage,
            m.date,
            m.home_team_api_id,
            m.away_team_api_id,
            m.home_team_goal,
            m.away_team_goal,
            l.name as league_name
        FROM Match m
        JOIN League l ON m.league_id = l.id
        WHERE m.home_team_goal IS NOT NULL
          AND m.away_team_goal IS NOT NULL
    """)
    rows = cursor.fetchall()

    imported = 0
    skipped = 0
    for api_id, season, stage, date_str, home_api, away_api, home_goals, away_goals, league in rows:
        home_id = kaggle_id_to_our_id.get(home_api)
        away_id = kaggle_id_to_our_id.get(away_api)
        if not home_id or not away_id:
            skipped += 1
            continue

        existing = session.query(Match).filter(Match.external_id == api_id).first()
        if existing:
            skipped += 1
            continue

        try:
            match_date = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        except:
            skipped += 1
            continue

        session.add(Match(
            external_id=api_id,
            home_team_id=home_id,
            away_team_id=away_id,
            match_date=match_date,
            competition=league,
            season=season,
            matchday=stage,
            home_goals=home_goals,
            away_goals=away_goals,
            status="FINISHED"
        ))
        imported += 1

        if imported % 500 == 0:
            session.commit()
            print(f"  {imported} matches imported so far...")

    session.commit()
    print(f"  Done: {imported} matches imported, {skipped} skipped")


def main():
    print("Starting Kaggle data import...")
    kaggle = sqlite3.connect(KAGGLE_DB)
    session = SessionLocal()

    try:
        kaggle_id_to_our_id = import_teams(kaggle, session)
        import_players(kaggle, session)
        import_matches(kaggle, session, kaggle_id_to_our_id)

        print()
        print("Import complete!")
        print(f"  Teams:   {session.query(Team).count()}")
        print(f"  Players: {session.query(Player).count()}")
        print(f"  Matches: {session.query(Match).count()}")

    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        raise
    finally:
        session.close()
        kaggle.close()


if __name__ == "__main__":
    main()
