from datetime import datetime, timezone

from celery import Celery

from .config import get_settings
from .db import SessionLocal
from .models import MailRecipient
from .services import mailer

_s = get_settings()
celery_app = Celery("documail", broker=_s.redis_url, backend=_s.redis_url)
celery_app.conf.task_always_eager = _s.celery_eager
celery_app.conf.task_eager_propagates = False


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def send_recipient_email(self, recipient_id: int) -> str:
    """One task per recipient so a single bad address never blocks the batch."""
    db = SessionLocal()
    try:
        r = db.get(MailRecipient, recipient_id)
        if r is None:
            return "missing"
        try:
            mailer.send_email(r.email, r.job.subject, r.job.body)
        except Exception as exc:  # noqa: BLE001
            if self.request.retries < self.max_retries and not _s.celery_eager:
                raise self.retry(exc=exc)
            r.status, r.error = "failed", str(exc)[:500]
        else:
            r.status, r.sent_at = "sent", datetime.now(timezone.utc)
        db.commit()
        return r.status
    finally:
        db.close()
