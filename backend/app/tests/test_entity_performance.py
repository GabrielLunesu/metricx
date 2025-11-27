"""
Tests for entity performance API (campaigns/ad sets).

WHAT:
    Validate backend/app/routers/entity_performance.py responses, ensuring
    filters, sorting, pagination, and trend payloads behave as expected.

WHY:
    Keeps campaigns UI contract stable and prevents regressions when tweaking
    aggregation logic or hierarchy handling.

REFERENCES:
    - app/routers/entity_performance.py
    - app/schemas.py::EntityPerformanceResponse
    - docs/metricx_BUILD_LOG.md (Campaigns integration entry)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Tuple

import pytest
from fastapi.testclient import TestClient
from fastapi import Depends

from app.main import create_app
from app.database import SessionLocal, get_db
from app import models


@pytest.fixture(autouse=True)
def _clean_db():
    session = SessionLocal()
    try:
        for model in (
            models.MetricFact,
            models.Entity,
            models.Connection,
            models.Import,
            models.Fetch,
            models.Workspace,
            models.Token,
            models.AuthCredential,
            models.QaQueryLog,
            models.ComputeRun,
            models.Pnl,
        ):
            session.query(model).delete()
        session.commit()
        yield
    finally:
        session.close()


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    app = create_app()
    with TestClient(app) as c:
        yield c


def _setup_workspace(db) -> Tuple[models.Workspace, models.Connection]:
    workspace = models.Workspace(id=uuid.uuid4(), name="Perf Workspace")
    db.add(workspace)
    db.flush()

    connection = models.Connection(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        provider=models.ProviderEnum.google,
        external_account_id="123-TEST",
        name="Google Test",
        status="active",
    )
    db.add(connection)
    db.flush()
    return workspace, connection


def _create_fact(db, entity_id, event_date, spend, revenue, clicks, impressions, conversions, import_id, level):
    fact = models.MetricFact(
        id=uuid.uuid4(),
        entity_id=entity_id,
        provider=models.ProviderEnum.google,
        level=level,
        event_at=event_date,
        event_date=event_date,
        spend=spend,
        revenue=revenue,
        clicks=clicks,
        impressions=impressions,
        conversions=conversions,
        currency="USD",
        natural_key=f"{entity_id}-{event_date.isoformat()}",
        ingested_at=datetime.utcnow(),
        import_id=import_id,
    )
    db.add(fact)


def _seed_entity_performance(db):
    workspace, connection = _setup_workspace(db)

    fetch = models.Fetch(
        id=uuid.uuid4(),
        connection_id=connection.id,
        kind="sync",
        status="completed",
        started_at=datetime.utcnow() - timedelta(days=7),
        finished_at=datetime.utcnow(),
        range_start=datetime.utcnow() - timedelta(days=7),
        range_end=datetime.utcnow(),
    )
    db.add(fetch)
    db.flush()
    import_record = models.Import(
        id=uuid.uuid4(),
        fetch_id=fetch.id,
        as_of=datetime.utcnow(),
        created_at=datetime.utcnow(),
        note="entity performance test",
    )
    db.add(import_record)
    db.flush()

    campaign_a = models.Entity(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        connection_id=connection.id,
        level=models.LevelEnum.campaign,
        external_id="CAMP-A",
        name="Campaign Alpha",
        status="active",
    )
    campaign_b = models.Entity(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        connection_id=connection.id,
        level=models.LevelEnum.campaign,
        external_id="CAMP-B",
        name="Campaign Beta",
        status="paused",
    )
    db.add_all([campaign_a, campaign_b])
    db.flush()

    adset_a1 = models.Entity(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        connection_id=connection.id,
        level=models.LevelEnum.adset,
        external_id="ADSET-A1",
        name="Prospecting",
        status="active",
        parent_id=campaign_a.id,
    )
    db.add(adset_a1)
    db.flush()

    for day_offset in range(5):
        day = datetime.utcnow() - timedelta(days=day_offset)
        _create_fact(db, campaign_a.id, day, spend=100 + day_offset, revenue=400 + 10 * day_offset, clicks=50, impressions=1000, conversions=10, import_id=import_record.id, level=models.LevelEnum.adset)
        _create_fact(db, campaign_b.id, day, spend=50, revenue=100, clicks=20, impressions=500, conversions=5, import_id=import_record.id, level=models.LevelEnum.adset)
        _create_fact(db, adset_a1.id, day, spend=60, revenue=210, clicks=40, impressions=800, conversions=6, import_id=import_record.id, level=models.LevelEnum.adset)

    db.commit()
    return workspace, campaign_a, adset_a1


def _auth_headers(workspace: models.Workspace) -> dict[str, str]:
    return {"X-Workspace-ID": str(workspace.id)}


@pytest.fixture(autouse=True)
def mock_auth(monkeypatch, db_session):
    workspace, _, _ = _seed_entity_performance(db_session)

    class FakeUser:
        def __init__(self, workspace_id):
            self.workspace_id = workspace_id

    def fake_get_current_user(db=Depends(get_db), access_token=None):  # type: ignore
        return FakeUser(workspace_id=str(workspace.id))

    from app import deps

    monkeypatch.setattr(deps, "get_current_user", fake_get_current_user)
    yield


def test_campaign_list_endpoint(client: TestClient, db_session):
    response = client.get(
        "/entity-performance/list",
        params={"entity_level": "campaign", "timeframe": "7d"},
        headers={"Cookie": "access_token=Bearer fake"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["title"] == "Campaigns"
    assert payload["pagination"]["total"] == 2
    assert len(payload["rows"]) == 2
    values = {row["name"]: row for row in payload["rows"]}
    assert values["Campaign Alpha"]["status"] == "active"
    assert values["Campaign Beta"]["status"] == "paused"


def test_adset_children_endpoint(client: TestClient, db_session):
    workspace, campaign, _ = _seed_entity_performance(db_session)
    response = client.get(
        f"/entity-performance/{campaign.id}/children",
        params={"timeframe": "7d"},
        headers={"Cookie": "access_token=Bearer fake"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["title"] == "Campaign Alpha"
    assert payload["pagination"]["total"] >= 1
    first_row = payload["rows"][0]
    assert first_row["trend_metric"] in {"roas", "revenue"}
    assert isinstance(first_row["trend"], list)

