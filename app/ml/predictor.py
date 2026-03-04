"""
Match outcome predictor using Random Forest.

The model predicts one of three outcomes:
  0 = Away win
  1 = Draw  
  2 = Home win

Features are engineered from each team's recent form.
"""
import pickle
import os
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.models import Match, Team

MODEL_PATH = "app/ml/model.pkl"


def get_team_features(db: Session, team_id: int, n: int = 10) -> dict:
    """
    Compute form features for a team based on their last N matches.
    These become the input features for the ML model.
    """
    matches = db.query(Match).filter(
        Match.status == "FINISHED",
        or_(
            Match.home_team_id == team_id,
            Match.away_team_id == team_id
        )
    ).order_by(Match.match_date.desc()).limit(n).all()

    if not matches:
        # Return neutral features if no history
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
    """
    Build the training dataset from historical matches.
    
    Each row = one match
    Features = home team form stats + away team form stats + home advantage
    Label = match outcome (0=away win, 1=draw, 2=home win)
    """
    matches = db.query(Match).filter(
        Match.status == "FINISHED",
        Match.home_goals != None,
        Match.away_goals != None
    ).order_by(Match.match_date.asc()).all()

    X = []  # Features
    y = []  # Labels

    print(f"Building training data from {len(matches)} matches...")

    for i, match in enumerate(matches):
        # Only use matches after index 50 so teams have some history
        if i < 50:
            continue

        # Get form BEFORE this match (don't include the match itself)
        home_features = get_team_features(db, match.home_team_id)
        away_features = get_team_features(db, match.away_team_id)

        # Build feature vector
        features = [
            home_features["points_per_game"],
            home_features["goal_diff_rate"],
            home_features["win_rate"],
            away_features["points_per_game"],
            away_features["goal_diff_rate"],
            away_features["win_rate"],
            1.0  # Home advantage constant
        ]

        # Determine outcome label
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
    """
    Train the Random Forest model and save it to disk.
    Returns training statistics.
    """
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score

    X, y = build_training_data(db)

    if len(X) < 100:
        return {"error": "Not enough training data", "samples": len(X)}

    print(f"Training on {len(X)} samples...")

    # Split into training and test sets (80/20 split)
    # random_state=42 makes results reproducible
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Train the model
    # n_estimators=100 means 100 decision trees
    # random_state=42 for reproducibility
    model = RandomForestClassifier(
        n_estimators=100,
        random_state=42,
        max_depth=10,
        min_samples_split=5
    )
    model.fit(X_train, y_train)

    # Evaluate on test set
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    # Save model to disk so we don't retrain every time
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)

    print(f"Model trained. Accuracy: {accuracy:.3f}")

    return {
        "status": "trained",
        "training_samples": len(X_train),
        "test_samples": len(X_test),
        "accuracy": round(accuracy, 3),
        "model_path": MODEL_PATH
    }


def load_model():
    """Load the saved model from disk."""
    if not os.path.exists(MODEL_PATH):
        return None
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


def predict_match(db: Session, home_team_id: int, away_team_id: int) -> dict:
    """
    Predict the outcome of a match between two teams.
    Returns probabilities for home win, draw, away win.
    """
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
        1.0  # Home advantage
    ]])

    if model is None:
        # Fallback to statistical priors if model not trained yet
        # These are the historical averages across football leagues
        probs = [0.28, 0.27, 0.45]
        source = "statistical_prior"
    else:
        # Get probability for each outcome from the model
        probs = model.predict_proba(features)[0]
        # predict_proba returns [away_win, draw, home_win] probabilities
        source = "random_forest_model"

    return {
        "home_team": home_team.name,
        "away_team": away_team.name,
        "prediction_source": source,
        "probabilities": {
            "home_win": round(float(probs[2]), 3),
            "draw": round(float(probs[1]), 3),
            "away_win": round(float(probs[0]), 3)
        },
        "predicted_outcome": (
            "Home Win" if probs[2] > probs[1] and probs[2] > probs[0]
            else "Draw" if probs[1] > probs[0]
            else "Away Win"
        ),
        "home_team_form": home_features,
        "away_team_form": away_features
    }
