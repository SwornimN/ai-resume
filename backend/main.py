import logging

from fastapi import FastAPI

from app.database import Base, engine
from app.routers import auth_router, job_postings_router, matches_router, resumes_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)

# Create all tables on startup (fine for dev; use Alembic for production).
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Resume-to-Job Matcher",
    description="Upload resumes, add job postings, and let AI score how well you match.",
    version="1.0.0",
)

app.include_router(auth_router.router)
app.include_router(resumes_router.router)
app.include_router(job_postings_router.router)
app.include_router(matches_router.router)


@app.get("/", tags=["health"])
def health_check():
    return {"status": "ok", "message": "Resume-to-Job Matcher API is running."}