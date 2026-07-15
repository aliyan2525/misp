def _signup_payload(email="founder@acme.com", password="Str0ngPass1", org="Acme Inc"):
    return {
        "email": email,
        "password": password,
        "full_name": "Founder Person",
        "org_name": org,
    }


def test_signup_succeeds_with_strong_password(client):
    response = client.post("/auth/signup", json=_signup_payload())
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_signup_rejects_weak_password(client):
    payload = _signup_payload(password="weak")
    response = client.post("/auth/signup", json=payload)
    assert response.status_code == 400
    assert "8 characters" in response.json()["detail"]


def test_signup_rejects_duplicate_email(client):
    client.post("/auth/signup", json=_signup_payload(email="dupe@acme.com"))
    response = client.post("/auth/signup", json=_signup_payload(email="dupe@acme.com"))
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


def test_login_succeeds_with_correct_credentials(client):
    client.post("/auth/signup", json=_signup_payload(email="login@acme.com"))
    response = client.post("/auth/login", json={"email": "login@acme.com", "password": "Str0ngPass1"})
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body


def test_login_fails_with_wrong_password(client):
    client.post("/auth/signup", json=_signup_payload(email="wrongpw@acme.com"))
    response = client.post("/auth/login", json={"email": "wrongpw@acme.com", "password": "totallywrong1"})
    assert response.status_code == 401


def test_refresh_token_issues_new_access_token(client):
    client.post("/auth/signup", json=_signup_payload(email="refresh@acme.com"))
    login_res = client.post("/auth/login", json={"email": "refresh@acme.com", "password": "Str0ngPass1"})
    refresh_token = login_res.json()["refresh_token"]

    refresh_res = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_res.status_code == 200
    assert "access_token" in refresh_res.json()


def test_refresh_rejects_garbage_token(client):
    response = client.post("/auth/refresh", json={"refresh_token": "not.a.real.token"})
    assert response.status_code == 401
