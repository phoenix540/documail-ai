import io

from conftest import register
from docx import Document as Docx

POLICY = (
    "Remote work policy. Employees may work remotely up to three days per week. "
    "Remote days must be agreed with the team lead. "
) * 3
OTHER = "Cafeteria menu. Pasta is served on Monday and fish is served on Friday. " * 3


def make_docx(text: str) -> bytes:
    buf = io.BytesIO()
    d = Docx()
    d.add_paragraph(text)
    d.save(buf)
    return buf.getvalue()


def upload(client, headers, name, data):
    return client.post("/documents", headers=headers, files={"file": (name, data)})


def test_upload_txt_and_docx(client, auth):
    assert upload(client, auth, "policy.txt", POLICY.encode()).status_code == 201
    r = upload(client, auth, "menu.docx", make_docx(OTHER))
    assert r.status_code == 201 and r.json()["n_chunks"] >= 1
    assert len(client.get("/documents", headers=auth).json()) == 2


def test_unsupported_and_empty_files(client, auth):
    assert upload(client, auth, "x.exe", b"abc").status_code == 415
    assert upload(client, auth, "empty.txt", b"   ").status_code == 422


def test_question_retrieves_the_right_document(client, auth):
    upload(client, auth, "policy.txt", POLICY.encode())
    upload(client, auth, "menu.txt", OTHER.encode())
    r = client.post("/chat", headers=auth, json={"message": "How many remote work days per week?"})
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "question"
    assert body["sources"][0]["filename"] == "policy.txt"
    # the prompt sent to the LLM contains the retrieved excerpt
    prompt = client.app.state.fake_llm.calls[-1][-1]["content"]
    assert "remotely" in prompt


def test_documents_are_private_per_user(client, auth):
    upload(client, auth, "policy.txt", POLICY.encode())
    other = register(client, "other@test.io")
    r = client.post("/chat", headers=other, json={"message": "remote work days"})
    assert r.json()["sources"] == []
    assert "No documents" in r.json()["answer"]


def test_delete_removes_vectors(client, auth):
    doc = upload(client, auth, "policy.txt", POLICY.encode()).json()
    assert client.delete(f"/documents/{doc['id']}", headers=auth).status_code == 204
    r = client.post("/chat", headers=auth, json={"message": "remote work"})
    assert r.json()["sources"] == []
