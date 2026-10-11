import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import ChatLog, User
from ..services import intent, rag
from ..services.llm import LLMUnavailable

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class Source(BaseModel):
    filename: str
    chunk: int
    score: float
    text: str


class EmailDraft(BaseModel):
    recipients: list[str]
    subject: str
    body: str


class ChatResponse(BaseModel):
    intent: str
    answer: str
    sources: list[Source] = []
    email_draft: EmailDraft | None = None  # the user must confirm before anything is sent


@router.post("", response_model=ChatResponse)
def chat(body: ChatRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    started = time.perf_counter()
    label = intent.predict(body.message)
    draft = None
    try:
        if label == "email":
            recipients = list(dict.fromkeys(intent.EMAIL_RE.findall(body.message)))
            topic = intent.EMAIL_RE.sub("", body.message).strip() or "the key points of my documents"
            text, sources = rag.answer(f"Write a short, professional email body about: {topic}", user.id)
            draft = EmailDraft(recipients=recipients, subject="Information from DocuMail AI", body=text)
            answer = f"I drafted an email for {', '.join(recipients)}. Review it, then confirm to send."
        elif label == "summary":
            answer, sources = rag.answer(f"Summarize the documents regarding: {body.message}", user.id)
        else:
            answer, sources = rag.answer(body.message, user.id)
    except LLMUnavailable as exc:
        raise HTTPException(503, str(exc))
    latency = int((time.perf_counter() - started) * 1000)
    db.add(ChatLog(user_id=user.id, message=body.message, intent=label, latency_ms=latency, n_sources=len(sources)))
    db.commit()
    return ChatResponse(intent=label, answer=answer, sources=[Source(**s) for s in sources], email_draft=draft)
