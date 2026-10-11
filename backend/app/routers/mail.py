from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import MailJob, MailRecipient, User
from ..tasks import send_recipient_email

router = APIRouter(prefix="/mail", tags=["mail"])


class SendRequest(BaseModel):
    recipients: list[EmailStr] = Field(min_length=1, max_length=500)
    subject: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1, max_length=20000)


class RecipientOut(BaseModel):
    email: str
    status: str
    error: str | None = None

    model_config = {"from_attributes": True}


class JobOut(BaseModel):
    id: int
    subject: str
    created_at: datetime
    recipients: list[RecipientOut]

    model_config = {"from_attributes": True}


def create_job(db: Session, user: User, recipients: list[str], subject: str, body: str) -> MailJob:
    job = MailJob(user_id=user.id, subject=subject, body=body)
    job.recipients = [MailRecipient(email=e.lower()) for e in dict.fromkeys(recipients)]
    db.add(job)
    db.commit()
    for r in job.recipients:
        send_recipient_email.delay(r.id)  # one Celery task per recipient
    db.refresh(job)
    return job


@router.post("/send", response_model=JobOut, status_code=202)
def send(body: SendRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return create_job(db, user, [str(e) for e in body.recipients], body.subject, body.body)


@router.get("/jobs", response_model=list[JobOut])
def jobs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(select(MailJob).where(MailJob.user_id == user.id).order_by(MailJob.id.desc()).limit(50)).all()


@router.get("/jobs/{job_id}", response_model=JobOut)
def job(job_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    j = db.get(MailJob, job_id)
    if not j or j.user_id != user.id:
        raise HTTPException(404, "Mail job not found")
    return j
