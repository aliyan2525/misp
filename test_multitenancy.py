import io


def _signup_and_login(client, email, org_name):
    client.post("/auth/signup", json={
        "email": email,
        "password": "Str0ngPass1",
        "full_name": "Test User",
        "org_name": org_name,
    })
    login_res = client.post("/auth/login", json={"email": email, "password": "Str0ngPass1"})
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _sample_csv_bytes():
    csv_content = (
        "campaign_name,channel,metric_date,clicks,impressions,cost,conversions\n"
        "Org Specific Campaign,Google Ads,2026-06-01,100,1000,50.00,10\n"
    )
    return csv_content.encode("utf-8")


def test_org_cannot_see_another_orgs_summary_metrics(client):
    headers_a = _signup_and_login(client, "orga@company.com", "Org A")
    headers_b = _signup_and_login(client, "orgb@company.com", "Org B")

    # Org A uploads data
    client.post(
        "/api/data/upload",
        headers=headers_a,
        files={"file": ("data.csv", _sample_csv_bytes(), "text/csv")},
    )

    # Org A sees its own data
    summary_a = client.get("/api/metrics/summary", headers=headers_a).json()
    assert summary_a["total_conversions"] == 10

    # Org B sees nothing — this is the core multi-tenancy guarantee
    summary_b = client.get("/api/metrics/summary", headers=headers_b).json()
    assert summary_b["total_conversions"] == 0
    assert summary_b["total_spend"] == 0.0


def test_org_cannot_see_another_orgs_recommendations(client):
    headers_a = _signup_and_login(client, "recA@company.com", "Rec Org A")
    headers_b = _signup_and_login(client, "recB@company.com", "Rec Org B")

    client.post(
        "/api/data/upload",
        headers=headers_a,
        files={"file": ("data.csv", _sample_csv_bytes(), "text/csv")},
    )

    recs_a = client.get("/api/recommendations", headers=headers_a).json()
    recs_b = client.get("/api/recommendations", headers=headers_b).json()

    # Org B's recommendation set must not reference Org A's campaign
    campaign_names_b = [r.get("campaign") for r in recs_b["recommendations"]]
    assert "Org Specific Campaign" not in campaign_names_b


def test_missing_auth_header_is_rejected(client):
    response = client.get("/api/metrics/summary")
    assert response.status_code in (401, 422)  # 422 if header missing entirely, 401 if invalid
