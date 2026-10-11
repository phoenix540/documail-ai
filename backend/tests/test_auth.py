from conftest import register


def test_first_user_is_admin_next_is_user(client):
    a = register(client, "a@test.io")
    b = register(client, "b@test.io")
    assert client.get("/auth/me", headers=a).json()["role"] == "admin"
    assert client.get("/auth/me", headers=b).json()["role"] == "user"


def test_duplicate_email_rejected(client):
    register(client, "a@test.io")
    r = client.post("/auth/register", json={"email": "A@test.io", "password": "password123"})
    assert r.status_code == 409


def test_login_wrong_password(client):
    register(client, "a@test.io")
    assert client.post("/auth/login", json={"email": "a@test.io", "password": "wrongpass1"}).status_code == 401
    assert client.post("/auth/login", json={"email": "a@test.io", "password": "password123"}).status_code == 200


def test_protected_routes_need_token(client):
    assert client.get("/documents").status_code == 401
    assert client.post("/chat", json={"message": "hi"}).status_code == 401


def test_only_admin_lists_users(client):
    a = register(client, "a@test.io")
    b = register(client, "b@test.io")
    assert client.get("/auth/users", headers=a).status_code == 200
    assert client.get("/auth/users", headers=b).status_code == 403
