import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["DB_NAME"] = "misp_test_db"

from database import Base
from models import Organization, User, Campaign, DailyMetric  # noqa: F401
from main import app, get_db, limiter
from fastapi.testclient import TestClient

# Rate limiting exists to protect real users from brute-force attacks — it's not
# something we want interfering with a test suite that legitimately calls
# /auth/signup and /auth/login many times in quick succession. Disable it for tests.
limiter.enabled = False

TEST_DB_USER = os.getenv("DB_USER", "postgres")
TEST_DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
TEST_DB_HOST = os.getenv("DB_HOST", "localhost")
TEST_DB_PORT = os.getenv("DB_PORT", "5432")
TEST_DATABASE_URL = f"postgresql://{TEST_DB_USER}:{TEST_DB_PASSWORD}@{TEST_DB_HOST}:{TEST_DB_PORT}/misp_test_db"

test_engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def create_test_schema():
    """Creates all tables once at the start of the test session, drops them at the end."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def db_session():
    """Gives each test a clean transaction that's rolled back afterward, so tests never
    leak data into each other."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    """FastAPI TestClient with the real get_db dependency swapped for our test session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
