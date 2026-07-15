from fastapi import FastAPI, Depends, HTTPException, Header, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import pandas as pd
from sqlalchemy import func, text
from sqlalchemy.orm import Session
import os
import io
from pydantic import BaseModel

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from database import engine, get_db
from models import Organization, User, Campaign, DailyMetric

# Internal Auth Imports (Ensure auth.py is in the same folder)
from auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    create_refresh_token,
    decode_refresh_token,
    is_password_strong,
)

# Phase 6 — Recommendation Engine imports
from recommendations import generate_recommendations
from forecasting import generate_conversion_forecast

# Phase 7 — Reporting imports
from reports import generate_pdf_report

# Phase 8 — Monitoring imports
from logging_config import logger
import sentry_sdk

sentry_sdk.init(dsn=os.getenv("SENTRY_DSN"), traces_sample_rate=0.5)

app = FastAPI(title="Marketing Intelligence Platform API")

# Rate limiting — protects auth endpoints from brute-force attempts
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Cross-Origin Resource Sharing configuration
# Set ALLOWED_ORIGINS in .env as a comma-separated list once you have a real frontend
# domain (e.g. "https://app.yourdomain.com,https://yourdomain.com"). Falls back to "*"
# for local development.
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "*")
allowed_origins = [o.strip() for o in allowed_origins_env.split(",")] if allowed_origins_env != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# Request Validations (Pydantic Models)
# ==========================================
class SignupRequest(BaseModel):
    email: str
    password: str
    full_name: str
    org_name: str

class LoginRequest(BaseModel):
    email: str
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

# Security Access Verification Dependency
def get_current_user(authorization: str = Header(...)):
    try:
        token = authorization.replace("Bearer ", "")
        payload = decode_access_token(token)
        if not payload or "org_id" not in payload:
            raise HTTPException(status_code=401, detail="Invalid workspace context token")
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Session expired or invalid token")

# ==========================================
# Health Check (point UptimeRobot / Sentry here)
# ==========================================
@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))  # cheap round-trip query to confirm connectivity
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {"status": "error", "detail": str(e)}

# ==========================================
# Authentication Service Endpoints
# ==========================================
@app.post("/auth/signup")
@limiter.limit("5/minute")
def signup(request: Request, body: SignupRequest, db: Session = Depends(get_db)):
    if not is_password_strong(body.password):
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters and include at least one digit."
        )

    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email address already registered.")

    org = Organization(name=body.org_name)
    db.add(org)
    db.flush()  # populates org.org_id without committing yet

    hashed = hash_password(body.password)
    user = User(
        org_id=org.org_id,
        email=body.email,
        hashed_password=hashed,
        full_name=body.full_name,
    )
    db.add(user)
    db.commit()

    return {"status": "success", "message": "Corporate workspace provisioned successfully."}

@app.post("/auth/login")
@limiter.limit("5/minute")
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    logger.info(f"Login attempt for {body.email}")
    user = db.query(User).filter(User.email == body.email).first()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or credentials.")

    token_payload = {"sub": str(user.user_id), "org_id": user.org_id}
    access_token = create_access_token(token_payload)
    refresh_token = create_refresh_token(token_payload)

    logger.info(f"Login successful for {body.email}")
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }

@app.post("/auth/refresh")
def refresh_access_token(body: RefreshRequest):
    payload = decode_refresh_token(body.refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Refresh token expired or invalid. Please log in again.")

    new_access_token = create_access_token({"sub": payload["sub"], "org_id": payload["org_id"]})
    return {"access_token": new_access_token, "token_type": "bearer"}

# ==========================================
# Multi-Tenant Core Reporting Layers
# ==========================================
@app.get("/api/metrics/summary")
def get_summary_metrics(user=Depends(get_current_user), db: Session = Depends(get_db)):
    result = (
        db.query(
            func.coalesce(func.sum(DailyMetric.cost), 0.0).label("total_spend"),
            func.coalesce(func.sum(DailyMetric.conversions), 0).label("total_conversions"),
            func.coalesce(func.sum(DailyMetric.clicks), 0).label("total_clicks"),
        )
        .join(Campaign, DailyMetric.campaign_id == Campaign.campaign_id)
        .filter(Campaign.org_id == user["org_id"])
        .first()
    )

    return {
        "total_spend": float(result.total_spend or 0.0),
        "total_conversions": int(result.total_conversions or 0),
        "total_clicks": int(result.total_clicks or 0),
    }

@app.get("/api/metrics/channels")
def get_channel_metrics(user=Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(
            DailyMetric.metric_date,
            Campaign.channel,
            func.sum(DailyMetric.conversions).label("total_conversions"),
        )
        .join(Campaign, DailyMetric.campaign_id == Campaign.campaign_id)
        .filter(Campaign.org_id == user["org_id"])
        .group_by(DailyMetric.metric_date, Campaign.channel)
        .order_by(DailyMetric.metric_date.asc())
        .all()
    )

    return [
        {
            "metric_date": r.metric_date.strftime("%Y-%m-%d"),
            "channel": r.channel,
            "total_conversions": int(r.total_conversions or 0),
        }
        for r in rows
    ]

@app.get("/api/metrics/performance")
def get_performance_metrics(user=Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(
            Campaign.channel,
            func.sum(DailyMetric.cost).label("total_cost"),
            func.sum(DailyMetric.conversions).label("total_conversions"),
        )
        .join(DailyMetric, Campaign.campaign_id == DailyMetric.campaign_id)
        .filter(Campaign.org_id == user["org_id"])
        .group_by(Campaign.channel)
        .all()
    )

    results = []
    for r in rows:
        total_cost = float(r.total_cost or 0)
        total_conversions = int(r.total_conversions or 0)
        rate = round((total_conversions / total_cost) * 100, 2) if total_cost > 0 else 0.0
        results.append({"channel": r.channel, "conversions_per_hundred_dollars": rate})

    return results

# ==========================================
# Phase 2 — CSV Data Import
# ==========================================
@app.post("/api/data/upload")
def upload_marketing_csv(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Unsupported file format. Please upload a standard CSV file.")

    logger.info(f"CSV upload started by org_id={user['org_id']}, filename={file.filename}")

    try:
        contents = file.file.read()
        df = pd.read_csv(io.BytesIO(contents))

        required_columns = {"campaign_name", "channel", "metric_date", "clicks", "impressions", "cost", "conversions"}
        if not required_columns.issubset(df.columns):
            raise HTTPException(
                status_code=400,
                detail=f"Structural mismatch. CSV missing tracking columns. Required: {list(required_columns)}",
            )

        for _, row in df.iterrows():
            campaign = (
                db.query(Campaign)
                .filter(Campaign.name == str(row["campaign_name"]), Campaign.org_id == user["org_id"])
                .first()
            )

            if not campaign:
                campaign = Campaign(
                    org_id=user["org_id"],
                    name=str(row["campaign_name"]),
                    channel=str(row["channel"]),
                    start_date=row["metric_date"],
                )
                db.add(campaign)
                db.flush()

            metric = DailyMetric(
                campaign_id=campaign.campaign_id,
                metric_date=row["metric_date"],
                clicks=int(row["clicks"]),
                impressions=int(row["impressions"]),
                cost=float(row["cost"]),
                conversions=int(row["conversions"]),
            )
            db.add(metric)

        db.commit()
        logger.info(f"CSV import successful for org_id={user['org_id']}: {len(df)} records")
        return {"status": "success", "message": f"Successfully integrated {len(df)} performance records."}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"CSV import failed for org_id={user['org_id']}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Data ingestion engine error: {str(e)}")

# ==========================================
# Phase 6 — Recommendation Engine
# ==========================================
@app.get("/api/recommendations")
def get_recommendations(user=Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(
            Campaign.name,
            func.sum(DailyMetric.cost).label("total_cost"),
            func.sum(DailyMetric.conversions).label("total_conversions"),
        )
        .join(DailyMetric, Campaign.campaign_id == DailyMetric.campaign_id)
        .filter(Campaign.org_id == user["org_id"])
        .group_by(Campaign.name)
        .all()
    )

    campaign_df = pd.DataFrame(
        [{"name": r.name, "total_cost": float(r.total_cost or 0), "total_conversions": int(r.total_conversions or 0)} for r in rows]
    )

    try:
        forecast_records = generate_conversion_forecast(org_id=user["org_id"], days_to_predict=30)
        forecast_df = pd.DataFrame(forecast_records)
    except Exception:
        forecast_df = pd.DataFrame()

    recs = generate_recommendations(campaign_df, forecast_df)
    return {"count": len(recs), "recommendations": recs}

# ==========================================
# Phase 7 — PDF Reporting
# ==========================================
@app.get("/api/reports/pdf")
def download_pdf_report(user=Depends(get_current_user), db: Session = Depends(get_db)):
    org = db.query(Organization).filter(Organization.org_id == user["org_id"]).first()

    rows = (
        db.query(
            Campaign.name,
            func.sum(DailyMetric.cost).label("total_cost"),
            func.sum(DailyMetric.conversions).label("total_conversions"),
        )
        .join(DailyMetric, Campaign.campaign_id == DailyMetric.campaign_id)
        .filter(Campaign.org_id == user["org_id"])
        .group_by(Campaign.name)
        .all()
    )

    campaign_df = pd.DataFrame(
        [{"name": r.name, "total_cost": float(r.total_cost or 0), "total_conversions": int(r.total_conversions or 0)} for r in rows]
    )

    try:
        forecast_records = generate_conversion_forecast(org_id=user["org_id"], days_to_predict=30)
        forecast_df = pd.DataFrame(forecast_records)
    except Exception:
        forecast_df = pd.DataFrame()

    recs = generate_recommendations(campaign_df, forecast_df)

    org_name = org.name if org else "Unknown Organization"
    pdf_bytes = generate_pdf_report(org_name, campaign_df, recs)
    logger.info(f"PDF report generated for org_id={user['org_id']} ({org_name})")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=marketing_report.pdf"},
    )
