# DocuMail AI

A document-grounded assistant: upload PDF/DOCX files, ask questions answered by a **local open-source LLM (Ollama)** with cited passages (**RAG**), and have the assistant **draft and send emails to many recipients** through a **Redis + Celery** queue. Built as a small-scale version of the PFE subject "Chatbot intelligent basé sur un LLM open source : RAG, Machine Learning et mailing".

## Architecture

```
React (Vite) ──HTTP/JWT──▶ FastAPI ──▶ PostgreSQL   users, documents, chat logs, mail jobs
                              │
                              ├──▶ sentence-transformers   multilingual FR/EN embeddings
                              ├──▶ ChromaDB                vector search (filtered per user)
                              ├──▶ Ollama                  local LLM (llama3.2:3b by default)
                              └──▶ Redis ──▶ Celery worker ──▶ SMTP (MailHog in dev)
```

| Subject level | Where it lives |
|---|---|
| 1. Auth, roles, upload + extraction, SMTP mailing | `routers/auth.py`, `services/extraction.py`, `routers/mail.py` |
| 2. RAG chatbot, embeddings, Redis + Celery | `services/rag.py`, `services/vectorstore.py`, `tasks.py` |
| 3. Intent model, statistics dashboard, evaluation | `services/intent.py` (baseline now), `routers/stats.py`, frontend Activity tab |

## Run it

```bash
cp .env.example .env          # set JWT_SECRET
docker compose up --build     # first start downloads the LLM, give it a few minutes
```

- App: http://localhost:5173 (the first account you create becomes admin)
- API docs: http://localhost:8000/docs
- Test inbox (MailHog): http://localhost:8025
- Slow answers? A 3B model on CPU takes 10-40 s. Use a GPU (add a `deploy.resources.reservations.devices` block to the `ollama` service) or set `OLLAMA_MODEL` to a smaller model.

## Tests

```bash
cd backend && pip install -r requirements-dev.txt && pytest
```

The tests use a fake embedder and fake LLM, so they run without Ollama or a GPU. They cover auth and roles, per-user document isolation, extraction (TXT/DOCX), retrieval, the email draft flow, per-recipient failure handling, and stats.

## Design choices worth explaining in an interview

- **The assistant never sends an email by itself.** An email request returns a draft; the user edits and confirms it in the UI, and only then does `/mail/send` queue it.
- **One Celery task per recipient**, so one bad address fails alone and the others still go out; each recipient has its own status.
- **Documents are private per user**: every vector query filters on `owner_id`.
- **The prompt forces citations** and tells the model to say when the answer is not in the documents. The Sources panel shows the exact passages used.

## Roadmap

1. **Done:** auth, upload/extraction, RAG, mailing queue, stats, UI.
2. **Evaluate the RAG:** write 20-30 question/answer pairs over sample documents and report retrieval hit rate (`backend/eval/`).
3. **Replace the intent baseline with a trained model:** label ~300 messages (FR/EN), train a scikit-learn or PyTorch classifier, and report accuracy/F1 against the keyword baseline.
4. **Polish:** Alembic migrations, OCR for scanned PDFs, streaming answers, a demo GIF in this README.

## Known limits

- Scanned PDFs have no text layer and are rejected (needs OCR).
- LangChain is currently used only for text splitting. Use it for the retrieval chain too if you want to claim it on your CV.
- The frontend runs the Vite dev server in Docker; build and serve static files for a real deployment.
