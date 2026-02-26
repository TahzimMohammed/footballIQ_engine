from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Team(Base):
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    short_name = Column(String, nullable=True)
    country = Column(String, nullable=True)
    founded = Column(Integer, nullable=True)
    stadium = Column(String, nullable=True)
    stadium_capacity = Column(Integer, nullable=True)
    manager = Column(String, nullable=True)
    external_id = Column(Integer, nullable=True)

    home_matches = relationship("Match", foreign_keys="Match.home_team_id", back_populates="home_team")
    away_matches = relationship("Match", foreign_keys="Match.away_team_id", back_populates="away_team")
    players = relationship("Player", back_populates="team")


class Player(Base):
    __tablename__ = "players"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    position = Column(String, nullable=True)
    nationality = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    shirt_number = Column(Integer, nullable=True)
    market_value_eur = Column(Float, nullable=True)
    external_id = Column(Integer, nullable=True)

    team = relationship("Team", back_populates="players")
    stats = relationship("PlayerStat", back_populates="player")


class Match(Base):
    __tablename__ = "matches"
    id = Column(Integer, primary_key=True, index=True)
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    match_date = Column(Date, nullable=False)
    competition = Column(String, nullable=True)
    season = Column(String, nullable=True)
    matchday = Column(Integer, nullable=True)
    home_goals = Column(Integer, nullable=True)
    away_goals = Column(Integer, nullable=True)
    xg_home = Column(Float, nullable=True)
    xg_away = Column(Float, nullable=True)
    status = Column(String, default="SCHEDULED")
    external_id = Column(Integer, nullable=True)

    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_matches")
    away_team = relationship("Team", foreign_keys=[away_team_id], back_populates="away_matches")
    player_stats = relationship("PlayerStat", back_populates="match")


class PlayerStat(Base):
    __tablename__ = "player_stats"
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    goals = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    minutes_played = Column(Integer, default=0)
    yellow_cards = Column(Integer, default=0)
    red_cards = Column(Integer, default=0)
    shots = Column(Integer, default=0)
    shots_on_target = Column(Integer, default=0)
    passes = Column(Integer, default=0)
    pass_accuracy = Column(Float, nullable=True)
    rating = Column(Float, nullable=True)

    player = relationship("Player", back_populates="stats")
    match = relationship("Match", back_populates="player_stats")
