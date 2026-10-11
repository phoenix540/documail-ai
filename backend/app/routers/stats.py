from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import ChatLog, Document, MailJob, MailRecipient, User

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("")
def stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    admin = user.role == "admin"  # admins see the whole workspace, users see their own activity
    scope = lambda col: (col.is_not(None) if admin else col == user.id)  # noqa: E731

    by_intent = dict(db.execute(select(ChatLog.intent, func.count()).where(scope(ChatLog.user_id)).group_by(ChatLog.intent)).all())
    per_day = db.execute(
        select(func.date(ChatLog.created_at), func.count()).where(scope(ChatLog.user_id)).group_by(func.date(ChatLog.created_at)).order_by(func.date(ChatLog.created_at))
    ).all()
    avg_latency = db.scalar(select(func.avg(ChatLog.latency_ms)).where(scope(ChatLog.user_id)))
    mail = dict(
        db.execute(
            select(MailRecipient.status, func.count()).join(MailJob, MailJob.id == MailRecipient.job_id).where(scope(MailJob.user_id)).group_by(MailRecipient.status)
        ).all()
    )
    return {
        "documents": db.scalar(select(func.count(Document.id)).where(scope(Document.owner_id))),
        "questions": sum(by_intent.values()),
        "by_intent": by_intent,
        "per_day": [{"day": str(d), "count": c} for d, c in per_day],
        "avg_latency_ms": round(avg_latency) if avg_latency else 0,
        "emails": {"sent": mail.get("sent", 0), "failed": mail.get("failed", 0), "queued": mail.get("queued", 0)},
    }
