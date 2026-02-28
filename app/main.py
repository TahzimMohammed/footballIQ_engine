from fastapi import FastAPI
from app.database import engine, Base
from app.routers import auth, teams

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FootballIQ API",
    description="Football performance and analytics API",
    version="1.0.0"
)

app.include_router(auth.router)
app.include_router(teams.router)


@app.get("/")
def root():
    return {"message": "Welcome to FootballIQ API", "docs": "/docs"}
