def _signup_and_login(client, email="uploader@company.com", org_name="Upload Test Org"):
    client.post("/auth/signup", json={
        "email": email,
        "password": "Str0ngPass1",
        "full_name": "Uploader Person",
        "org_name": org_name,
    })
    login_res = client.post("/auth/login", json={"email": email, "password": "Str0ngPass1"})
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_upload_rejects_non_csv_file(client):
    headers = _signup_and_login(client)
    response = client.post(
        "/api/data/upload",
        headers=headers,
        files={"file": ("data.txt", b"not a csv", "text/plain")},
    )
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


def test_upload_rejects_csv_missing_required_columns(client):
    headers = _signup_and_login(client, email="missingcols@company.com")
    bad_csv = "campaign_name,channel\nSome Campaign,Google Ads\n".encode("utf-8")
    response = client.post(
        "/api/data/upload",
        headers=headers,
        files={"file": ("data.csv", bad_csv, "text/csv")},
    )
    assert response.status_code == 400
    assert "Structural mismatch" in response.json()["detail"]


def test_upload_succeeds_with_valid_csv(client):
    headers = _signup_and_login(client, email="validupload@company.com")
    good_csv = (
        "campaign_name,channel,metric_date,clicks,impressions,cost,conversions\n"
        "Valid Campaign,Facebook Ads,2026-06-01,50,500,25.00,5\n"
        "Valid Campaign,Facebook Ads,2026-06-02,60,600,30.00,8\n"
    ).encode("utf-8")

    response = client.post(
        "/api/data/upload",
        headers=headers,
        files={"file": ("data.csv", good_csv, "text/csv")},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    summary = client.get("/api/metrics/summary", headers=headers).json()
    assert summary["total_conversions"] == 13
    assert summary["total_clicks"] == 110
