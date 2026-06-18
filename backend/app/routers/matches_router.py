import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import JobPosting, Match, Resume, User
from app.schemas import MatchCreate, MatchOut
from app.services import ai_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/matches", tags=["matches"])


def _get_resume_for_user(resume_id: int, user_id: int, db: Session) -> Resume:
    resume = db.get(Resume, resume_id)
    if not resume or resume.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume {resume_id} not found.",
        )
    return resume


def _get_job_posting_for_user(
    posting_id: int, user_id: int, db: Session
) -> JobPosting:
    posting = db.get(JobPosting, posting_id)
    if not posting or posting.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job posting {posting_id} not found.",
        )
    return posting


@router.post("/", response_model=MatchOut, status_code=status.HTTP_201_CREATED)
def create_match(
    payload: MatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resume = _get_resume_for_user(payload.resume_id, current_user.id, db)
    posting = _get_job_posting_for_user(
        payload.job_posting_id, current_user.id, db
    )

    if resume.parsed_json is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Resume has not been successfully parsed yet. "
                "Re-upload the PDF or wait for AI extraction to complete."
            ),
        )
    if posting.parsed_json is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Job posting has not been successfully parsed yet. "
                "Re-create the posting or wait for AI extraction to complete."
            ),
        )

    match_score = None
    matched_skills = None
    missing_skills = None
    suggestions = None

    try:
        result = ai_service.compare_resume_to_job(resume.parsed_json, posting.parsed_json)
        match_score = float(result.get("match_score", 0))
        matched_skills = result.get("matched_skills", [])
        missing_skills = result.get("missing_skills", [])
        suggestions = result.get("suggestions", "")
    except Exception:
        logger.exception(
            "AI comparison failed for resume %d vs job posting %d.",
            resume.id,
            posting.id,
        )

    match = Match(
        resume_id=resume.id,
        job_posting_id=posting.id,
        match_score=match_score,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        suggestions=suggestions,
    )
    db.add(match)
    db.commit()
    db.refresh(match)
    return match


@router.get("/{match_id}", response_model=MatchOut)
def get_match(
    match_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    match = db.get(Match, match_id)
    # Ownership check: match belongs to user if the underlying resume does.
    if not match or match.resume.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Match {match_id} not found.",
        )
    return match


@router.get("/", response_model=list[MatchOut])
def list_matches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Match)
        .join(Resume, Match.resume_id == Resume.id)
        .filter(Resume.user_id == current_user.id)
        .all()
    )
