from functools import lru_cache

import chromadb

from ..config import get_settings


@lru_cache
def get_client():
    return chromadb.PersistentClient(path=get_settings().chroma_path)


def get_collection():
    return get_client().get_or_create_collection(get_settings().chroma_collection, metadata={"hnsw:space": "cosine"})


def add_chunks(doc_id: int, owner_id: int, filename: str, chunks: list[str], embeddings: list[list[float]]) -> None:
    get_collection().add(
        ids=[f"{doc_id}:{i}" for i in range(len(chunks))],
        documents=chunks,
        embeddings=embeddings,
        metadatas=[{"doc_id": doc_id, "owner_id": owner_id, "filename": filename, "chunk": i} for i in range(len(chunks))],
    )


def query(embedding: list[float], owner_id: int, k: int) -> list[dict]:
    res = get_collection().query(query_embeddings=[embedding], n_results=k, where={"owner_id": owner_id})
    out = []
    for text, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        out.append({"text": text, "filename": meta["filename"], "doc_id": meta["doc_id"], "chunk": meta["chunk"], "score": round(1 - dist, 4)})
    return out


def delete_document(doc_id: int) -> None:
    get_collection().delete(where={"doc_id": doc_id})
