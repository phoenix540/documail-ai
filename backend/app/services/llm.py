import httpx

from ..config import get_settings


class LLMUnavailable(RuntimeError):
    pass


class OllamaClient:
    def chat(self, messages: list[dict]) -> str:
        s = get_settings()
        try:
            r = httpx.post(
                f"{s.ollama_url}/api/chat",
                json={"model": s.ollama_model, "messages": messages, "stream": False, "options": {"temperature": 0.2}},
                timeout=180,
            )
            r.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMUnavailable(f"Ollama is not reachable or the model '{s.ollama_model}' is not pulled ({exc.__class__.__name__}).") from exc
        return r.json()["message"]["content"].strip()


def get_llm():
    return OllamaClient()
