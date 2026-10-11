import hashlib
import math
import os
import re
import tempfile
import uuid

_tmp = tempfile.mkdtemp()
os.environ.update(
    DATABASE_URL=f"sqlite:///{_tmp}/test.db",
    CELERY_EAGER="1",
    JWT_SECRET="test-secret",
    CHROMA_PATH=f"{_tmp}/chroma",
)

import chromadb  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services import embeddings, llm, mailer, vectorstore  # noqa: E402


class FakeEmbedder:
    """Deterministic bag-of-words hashing embedder: similar words give similar vectors."""

    DIM = 256

    def embed(self, texts):
        out = []
        for t in texts:
            v = [0.0] * self.DIM
            for w in re.findall(r"\w+", t.lower()):
                v[int(hashlib.md5(w.encode()).hexdigest(), 16) % self.DIM] += 1.0
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / n for x in v])
        return out


class FakeLLM:
    def __init__(self):
        self.calls = []

    def chat(self, messages):
        self.calls.append(messages)
        return "Fake answer based on the excerpts [1]."


@pytest.fixture(autouse=True)
def env(monkeypatch):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    client = chromadb.EphemeralClient()
    monkeypatch.setattr(get_settings(), "chroma_collection", f"t_{uuid.uuid4().hex}")
    monkeypatch.setattr(vectorstore, "get_client", lambda: client)
    monkeypatch.setattr(embeddings, "get_embedder", lambda: FakeEmbedder())
    fake_llm = FakeLLM()
    monkeypatch.setattr(llm, "get_llm", lambda: fake_llm)
    sent = []
    monkeypatch.setattr(mailer, "send_email", lambda to, subject, body: sent.append((to, subject, body)))
    app.state.fake_llm, app.state.sent = fake_llm, sent
    yield


@pytest.fixture
def client():
    return TestClient(app)


def register(client, email="admin@test.io", password="password123"):
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def auth(client):
    return register(client)
