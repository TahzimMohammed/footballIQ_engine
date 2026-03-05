import pickle
import os
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.models import Match, Team

MODEL_PATH = "app/ml/model.pkl"


def get_team_features(db: Session, team_id: int, n: int = 10) -> dict:
    matches = db.query(Match).filter(
        Match.status == "FINISHED",
        or_(
            Match.home_team_id == team_id,
            Match.away_team_id == team_id
        )
    ).order_by(Match.match_date.desc()).limit(n).all()

    if not matches:
        return {"points_per_game": 1.0, "goal_diff_rate": 0.0, "win_rate": 0.33}

    total_points = 0
    total_gd = 0
    wins = 0

    for match in matches:
        is_home = match.home_team_id == team_id
        gf = (match.home_goals if is_home else match.away_goals) or 0
        ga = (match.away_goals if is_home else match.home_goals) or 0

        if gf > ga:
            total_points += 3
            wins += 1
        elif gf == ga:
            total_points += 1

        total_gd += (gf - ga)

    n_matches = len(matches)
    return {
        "points_per_game": total_points / n_matches,
        "goal_diff_rate": total_gd / n_matches,
        "win_rate": wins / n_matches
    }


def build_training_data(db: Session):
    matches = db.query(Match).filter(
        Match.status == "FINISHED",
        Match.home_goals != None,
        Match.away_goals != None
    ).order_by(Match.match_date.asc()).all()

    X = []
    y = []

    print(f"Building training data from {len(matches)} matches...")

    for i, match in enumerate(matches):
        if i < 50:
            continue

        home_features = get_team_features(db, match.home_team_id)
        away_features = get_team_features(db, match.away_team_id)

        features = [
            home_features["points_per_game"],
            home_features["goal_diff_rate"],
            home_features["win_rate"],
            away_features["points_per_game"],
            away_features["goal_diff_rate"],
            away_features["win_rate"],
            1.0
        ]

        hg = match.home_goals
        ag = match.away_goals
        if hg > ag:
            label = 2  # Home win
        elif hg == ag:
            label = 1  # Draw
        else:
            label = 0  # Away win

        X.append(features)
        y.append(label)

    return np.array(X), np.array(y)


def train_model(db: Session) -> dict:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score

    X, y = build_training_data(db)

    if len(X) < 100:
        return {"error": "Not enough training data", "samples": len(X)}

    print(f"Training on {len(X)} samples...")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = RandomForestClassifier(
        n_estimators=100,
        random_state=42,
        max_depth=10,
        min_samples_split=5
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)

    print(f"Model trained. Accuracy: {accuracy:.3f}")
    print(f"Classes: {model.classes_}")

    return {
        "status": "trained",
        "training_samples": len(X_train),
        "test_samples": len(X_test),
        "accuracy": round(accuracy, 3),
        "model_path": MODEL_PATH
    }


def load_model():
    if not os.path.exists(MODEL_PATH):
        return None
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


def predict_match(db: Session, home_team_id: int, away_team_id: int) -> dict:
    model = load_model()

    home_team = db.query(Team).filter(Team.id == home_team_id).first()
    away_team = db.query(Team).filter(Team.id == away_team_id).first()

    if not home_team or not away_team:
        return None

    home_features = get_team_features(db, home_team_id)
    away_features = get_team_features(db, away_team_id)

    features = np.array([[
        home_features["points_per_game"],
        home_features["goal_diff_rate"],
        home_features["win_rate"],
        away_features["points_per_game"],
        away_features["goal_diff_rate"],
        away_features["win_rate"],
        1.0
    ]])

    if model is None:
        probs_list = [0.28, 0.27, 0.45]
        source = "statistical_prior"
    else:
        raw_probs = model.predict_proba(features)[0]
        # model.classes_ = [0, 1, 2] = [away_win, draw, home_win]
        # Build a dict keyed by class label for safe lookup
        class_probs = {model.classes_[i]: float(raw_probs[i]) for i in range(len(raw_probs))}
        probs_list = [
            class_probs.get(0, 0.0),  # away win
            class_probs.get(1, 0.0),  # draw
            class_probs.get(2, 0.0),  # home win
        ]
        source = "random_forest_model"

    home_win_prob = probs_list[2]
    draw_prob = probs_list[1]
    away_win_prob = probs_list[0]

    if home_win_prob > draw_prob and home_win_prob > away_win_prob:
        outcome = "Home Win"
    elif draw_prob > away_win_prob:
        outcome = "Draw"
    else:
        outcome = "Away Win"

    return {
        "home_team": home_team.name,
        "away_team": away_team.name,
        "prediction_source": source,
        "probabilities": {
            "home_win": round(home_win_prob, 3),
            "draw": round(draw_prob, 3),
            "away_win": round(away_win_prob, 3)
        },
        "predicted_outcome": outcome,
        "home_team_form": home_features,
        "away_team_form": away_features
    }
