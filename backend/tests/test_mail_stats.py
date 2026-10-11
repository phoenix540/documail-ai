from conftest import register
from test_rag import POLICY, upload


def test_bulk_mail_one_task_per_recipient(client, auth):
    r = client.post("/mail/send", headers=auth, json={"recipients": ["a@x.io", "b@x.io", "a@x.io"], "subject": "Hello", "body": "Body"})
    assert r.status_code == 202
    job = client.get(f"/mail/jobs/{r.json()['id']}", headers=auth).json()
    assert sorted(x["email"] for x in job["recipients"]) == ["a@x.io", "b@x.io"]  # de-duplicated
    assert all(x["status"] == "sent" for x in job["recipients"])
    assert len(client.app.state.sent) == 2


def test_failed_recipient_does_not_block_others(client, auth, monkeypatch):
    from app.services import mailer

    def flaky(to, subject, body):
        if to == "bad@x.io":
            raise ConnectionError("550 mailbox unavailable")
        client.app.state.sent.append(to)

    monkeypatch.setattr(mailer, "send_email", flaky)
    r = client.post("/mail/send", headers=auth, json={"recipients": ["bad@x.io", "ok@x.io"], "subject": "S", "body": "B"})
    status = {x["email"]: x["status"] for x in r.json()["recipients"]}
    assert status == {"bad@x.io": "failed", "ok@x.io": "sent"}


def test_invalid_email_rejected(client, auth):
    r = client.post("/mail/send", headers=auth, json={"recipients": ["not-an-email"], "subject": "S", "body": "B"})
    assert r.status_code == 422


def test_mail_jobs_are_private(client, auth):
    job = client.post("/mail/send", headers=auth, json={"recipients": ["a@x.io"], "subject": "S", "body": "B"}).json()
    other = register(client, "other@test.io")
    assert client.get(f"/mail/jobs/{job['id']}", headers=other).status_code == 404


def test_chat_email_intent_returns_draft_and_sends_nothing(client, auth):
    upload(client, auth, "policy.txt", POLICY.encode())
    r = client.post("/chat", headers=auth, json={"message": "Send the remote work policy by email to sara@x.io and omar@x.io"})
    body = r.json()
    assert body["intent"] == "email"
    assert body["email_draft"]["recipients"] == ["sara@x.io", "omar@x.io"]
    assert client.app.state.sent == []  # nothing leaves without the user's confirmation


def test_intent_french_and_summary(client, auth):
    assert client.post("/chat", headers=auth, json={"message": "Envoie le planning à marie@x.io"}).json()["intent"] == "email"
    assert client.post("/chat", headers=auth, json={"message": "Résume le document"}).json()["intent"] == "summary"


def test_stats_reflect_activity(client, auth):
    upload(client, auth, "policy.txt", POLICY.encode())
    client.post("/chat", headers=auth, json={"message": "remote work?"})
    client.post("/chat", headers=auth, json={"message": "Summarize the policy"})
    client.post("/mail/send", headers=auth, json={"recipients": ["a@x.io"], "subject": "S", "body": "B"})
    s = client.get("/stats", headers=auth).json()
    assert s["documents"] == 1 and s["questions"] == 2
    assert s["by_intent"] == {"question": 1, "summary": 1}
    assert s["emails"]["sent"] == 1
    assert len(s["per_day"]) == 1
