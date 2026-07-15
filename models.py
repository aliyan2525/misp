from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Date, Numeric, func
from sqlalchemy.orm import relationship

from database import Base


class Organization(Base):
    __tablename__ = "organizations"

    org_id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    users = relationship("User", back_populates="organization")
    campaigns = relationship("Campaign", back_populates="organization")


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("organizations.org_id"), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(String(50), server_default="member")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    organization = relationship("Organization", back_populates="users")


class Campaign(Base):
    __tablename__ = "campaigns"

    campaign_id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("organizations.org_id"), nullable=False)
    name = Column(String(255), nullable=False)
    channel = Column(String(100))
    start_date = Column(Date)

    organization = relationship("Organization", back_populates="campaigns")
    daily_metrics = relationship("DailyMetric", back_populates="campaign", cascade="all, delete-orphan")


class DailyMetric(Base):
    __tablename__ = "daily_metrics"

    metric_id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.campaign_id"), nullable=False)
    metric_date = Column(Date, nullable=False)
    clicks = Column(Integer, server_default="0")
    impressions = Column(Integer, server_default="0")
    cost = Column(Numeric(10, 2), server_default="0")
    conversions = Column(Integer, server_default="0")

    campaign = relationship("Campaign", back_populates="daily_metrics")
