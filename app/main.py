from fastapi import FastAPI
from app.database import engine, Base
from app.routers import auth, teams, players, matches, analytics
from app.graphql_schema import graphql_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FootballIQ_Engine API",
    description="Football performance and analytics API",
    version="1.0.0"
)

app.include_router(auth.router)
app.include_router(teams.router)
app.include_router(players.router)
app.include_router(matches.router)
app.include_router(analytics.router)

# GraphQL is mounted at /graphql
# graphiql=True enables the interactive GraphQL playground
app.include_router(graphql_router, prefix="/graphql")


@app.get("/")
def root():
    return {"message": "Welcome to FootballIQ_Engine API", "docs": "/docs", "graphql": "/graphql"}
