import sys
import os

# Add padosi root so src/ can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine
import models
from routes import auth as auth_router, review as review_router

models.Base.metadata.create_all(bind=engine)


# Seed a demo user on startup if DB is empty
from database import SessionLocal
from auth import get_password_hash
_db = SessionLocal()
if _db.query(models.User).count() == 0:
    demo_user = models.User(
        email="demo@example.com",
        username="demo",
        hashed_password=get_password_hash("demo123"),
    )
    _db.add(demo_user)
    _db.commit()
_db.close()


def get_allowed_origins():
    raw_origins = os.getenv("CORS_ALLOW_ORIGINS", "")
    origins = {origin.strip() for origin in raw_origins.split(",") if origin.strip()}
    if not origins:
        origins = {
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:3002",
            "http://localhost:3003",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
            "http://127.0.0.1:3002",
            "http://127.0.0.1:3003",
        }
    return sorted(origins)


app = FastAPI(title="SafeCodeAI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(review_router.router)


@app.get("/")
def root():
    return {"status": "ok", "message": "SafeCodeAI API"}


@app.get("/health")
def health():
    return {"status": "healthy"}
