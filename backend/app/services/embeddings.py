from functools import lru_cache

from ..config import get_settings


class SentenceTransformerEmbedder:
    """Multilingual (FR/EN) sentence embeddings, loaded lazily on first use."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model.encode(texts, normalize_embeddings=True).tolist()


@lru_cache
def get_embedder():
    return SentenceTransformerEmbedder(get_settings().embedding_model)
