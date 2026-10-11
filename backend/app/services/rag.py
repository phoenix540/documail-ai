from . import embeddings, llm, vectorstore
from ..config import get_settings

SYSTEM = (
    "You are DocuMail AI, an assistant that answers strictly from the provided document excerpts. "
    "Answer in the same language as the question. Cite the excerpts you used like [1], [2]. "
    "If the excerpts do not contain the answer, say you could not find it in the documents. Do not invent facts."
)


def retrieve(question: str, owner_id: int) -> list[dict]:
    vec = embeddings.get_embedder().embed([question])[0]
    return vectorstore.query(vec, owner_id, get_settings().rag_top_k)


def answer(question: str, owner_id: int) -> tuple[str, list[dict]]:
    sources = retrieve(question, owner_id)
    if not sources:
        return "No documents are indexed yet. Upload a PDF or DOCX first.", []
    context = "\n\n".join(f"[{i + 1}] ({s['filename']})\n{s['text']}" for i, s in enumerate(sources))
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"Excerpts:\n{context}\n\nQuestion: {question}"},
    ]
    return llm.get_llm().chat(messages), sources
