from fastapi import FastAPI
from app.database import engine, Base
from app.routers import auth, teams, players, matches, analytics

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FootballIQ API",
    description="Football performance and analytics API",
    version="1.0.0"
)

app.include_router(auth.router)
app.include_router(teams.router)
app.include_router(players.router)
app.include_router(matches.router)
app.include_router(analytics.router)


@app.get("/")
def root():
    return {"message": "Welcome to FootballIQ API", "docs": "/docs"}
