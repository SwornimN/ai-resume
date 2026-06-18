import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import JobPosting, User
from app.schemas import JobPostingCreate, JobPostingOut
from app.services import ai_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/job-postings", tags=["job-postings"])


@router.post("/", response_model=JobPostingOut, status_code=status.HTTP_201_CREATED)
def create_job_posting(
    payload: JobPostingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Attempt AI extraction — failures are non-fatal.
    parsed_json = None
    try:
        parsed_json = ai_service.extract_structured_data(payload.raw_text)
    except Exception:
        logger.exception(
            "AI extraction failed for job posting '%s' at '%s'; storing raw text only.",
            payload.title,
            payload.company,
        )

    posting = JobPosting(
        user_id=current_user.id,
        title=payload.title,
        company=payload.company,
        raw_text=payload.raw_text,
        parsed_json=parsed_json,
    )
    db.add(posting)
    db.commit()
    db.refresh(posting)
    return posting


@router.get("/", response_model=list[JobPostingOut])
def list_job_postings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(JobPosting).filter(JobPosting.user_id == current_user.id).all()
    )
