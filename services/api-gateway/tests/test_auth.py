from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.main import app


@pytest.fixture
def client(monkeypatch, tmp_path: Path):
	test_db_path = tmp_path / "auth-test.db"
	test_database_url = f"sqlite+pysqlite:///{test_db_path}"
	test_engine = create_engine(test_database_url, connect_args={"check_same_thread": False})
	test_session_factory = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

	monkeypatch.setattr("app.db.init_db.engine", test_engine)
	monkeypatch.setattr("app.db.session.engine", test_engine)
	Base.metadata.create_all(bind=test_engine)

	def override_get_db():
		db = test_session_factory()
		try:
			yield db
		finally:
			db.close()

	from app.db.session import get_db

	app.dependency_overrides[get_db] = override_get_db
	with TestClient(app) as test_client:
		yield test_client
	app.dependency_overrides.clear()


def test_register_creates_user_and_session(client: TestClient):
	response = client.post(
		"/api/v1/auth/register",
		json={"email": "new.engineer@aegisops.ai", "password": "Password123!"},
	)

	assert response.status_code == 201
	body = response.json()
	assert body["access_token"]
	assert body["refresh_token"]


def test_register_rejects_duplicate_email(client: TestClient):
	first = client.post(
		"/api/v1/auth/register",
		json={"email": "duplicate.engineer@aegisops.ai", "password": "Password123!"},
	)
	assert first.status_code == 201

	second = client.post(
		"/api/v1/auth/register",
		json={"email": "duplicate.engineer@aegisops.ai", "password": "Password123!"},
	)

	assert second.status_code == 409
	assert second.json()["detail"] == "email_already_registered"