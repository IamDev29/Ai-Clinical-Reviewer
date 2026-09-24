"""Pytest fixtures for test database session and FastAPI TestClient."""
import os
import sys
import shutil
from typing import Generator
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

# Add backend directory to sys.path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.base import Base
from app.db.session import get_db, SessionLocal
import app.db.session as session_module
from app.main import app
from app.core.config import settings

TEST_DATABASE_URL = "sqlite:///./test.db"
TEST_UPLOAD_DIR = "./test_storage/uploads"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Monkeypatch SessionLocal in session_module so background tasks use test_engine
session_module.SessionLocal = TestingSessionLocal
settings.UPLOAD_DIR = TEST_UPLOAD_DIR


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Create all tables and test upload directory for the test session."""
    Base.metadata.create_all(bind=test_engine)
    os.makedirs(TEST_UPLOAD_DIR, exist_ok=True)

    yield

    Base.metadata.drop_all(bind=test_engine)
    if os.path.exists("./test.db"):
        try:
            os.remove("./test.db")
        except OSError:
            pass
    if os.path.exists("./test_storage"):
        try:
            shutil.rmtree("./test_storage")
        except OSError:
            pass


@pytest.fixture
def db() -> Generator[Session, None, None]:
    """Provide a database session for test queries."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db: Session) -> Generator[TestClient, None, None]:
    """Provide a TestClient with overridden get_db dependency."""
    def _override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
