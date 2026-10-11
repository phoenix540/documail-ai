from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import Document, User
from ..services import chunking, embeddings, extraction, vectorstore

router = APIRouter(prefix="/documents", tags=["documents"])
MAX_BYTES = 15 * 1024 * 1024


class DocumentOut(BaseModel):
    id: int
    filename: str
    n_chunks: int
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("", response_model=list[DocumentOut])
def list_documents(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(select(Document).where(Document.owner_id == user.id).order_by(Document.id.desc())).all()


@router.post("", response_model=DocumentOut, status_code=201)
async def upload(file: UploadFile, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File is larger than 15 MB")
    try:
        text = extraction.extract_text(file.filename or "", data)
    except extraction.UnsupportedFile as exc:
        raise HTTPException(415, str(exc))
    except Exception:  # corrupt or encrypted file
        raise HTTPException(422, "This file could not be read. Check that it is not corrupted or password-protected.")
    chunks = chunking.split_text(text)
    if not chunks:
        raise HTTPException(422, "No text found in this file. Scanned PDFs need OCR first.")
    doc = Document(owner_id=user.id, filename=file.filename, n_chunks=len(chunks))
    db.add(doc)
    db.flush()
    vectors = embeddings.get_embedder().embed(chunks)
    vectorstore.add_chunks(doc.id, user.id, doc.filename, chunks, vectors)
    db.commit()
    return doc


@router.delete("/{doc_id}", status_code=204)
def delete(doc_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if not doc or doc.owner_id != user.id:
        raise HTTPException(404, "Document not found")
    vectorstore.delete_document(doc.id)
    db.delete(doc)
    db.commit()
