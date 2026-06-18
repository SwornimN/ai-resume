from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr


# ── Auth ─────────────────────────────────────────────────────────────────────


class SignupRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Resumes ───────────────────────────────────────────────────────────────────


class ResumeOut(BaseModel):
    id: int
    user_id: int
    filename: str
    raw_text: str
    parsed_json: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Job Postings ──────────────────────────────────────────────────────────────


class JobPostingCreate(BaseModel):
    title: str
    company: str
    raw_text: str


class JobPostingOut(BaseModel):
    id: int
    user_id: int
    title: str
    company: str
    raw_text: str
    parsed_json: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Matches ───────────────────────────────────────────────────────────────────


class MatchCreate(BaseModel):
    resume_id: int
    job_posting_id: int


class MatchOut(BaseModel):
    id: int
    resume_id: int
    job_posting_id: int
    match_score: float | None
    matched_skills: list[str] | None
    missing_skills: list[str] | None
    suggestions: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
