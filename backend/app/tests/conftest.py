"""Pytest configuration for app integration tests

WHAT: Provides shared fixtures for HTTP endpoint and system-level tests
WHY: Ensures consistent test setup, database isolation, and mock configuration
REFERENCES:
    - app/main.py: FastAPI application
    - app/database.py: Database configuration
    - app/deps.py: Dependency injection
    - app/services/qa_service.py: QA service
"""

import pytest
import os
import json
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

# Ensure backend is in path
import sys
from pathlib import Path
BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Set test environment
os.environ.setdefault("JWT_SECRET", "test-jwt-secret")
# Must be URL-safe base64-encoded 32-byte string (app.security validates at import time)
os.environ.setdefault("TOKEN_ENCRYPTION_KEY", "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("OPENAI_API_KEY", "test-api-key")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
def test_db_engine():
    """Create in-memory test database engine."""
    # Use SQLite in-memory for fast tests
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )

    # Create all tables
    from app.database import Base
    Base.metadata.create_all(bind=engine)

    yield engine

    # Cleanup
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_db_session(test_db_engine) -> Generator[Session, None, None]:
    """Create test database session with rollback."""
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_db_engine
    )

    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


# ============================================================================
# Application & Client Fixtures
# ============================================================================

@pytest.fixture
def app(test_db_session):
    """Create FastAPI test application."""
    from app.main import create_app

    test_app = create_app()

    # Override database dependency
    from app.database import get_db

    def override_get_db():
        try:
            yield test_db_session
        finally:
            test_db_session.close()

    test_app.dependency_overrides[get_db] = override_get_db

    return test_app


@pytest.fixture
def client(app) -> TestClient:
    """Create TestClient for HTTP testing."""
    return TestClient(app)


# ============================================================================
# Authentication Fixtures
# ============================================================================

@pytest.fixture
def test_user_token():
    """Generate test JWT token."""
    from jose import jwt
    from datetime import timedelta

    data = {
        "sub": "test-user-123",
        "workspace_id": "test-workspace-123",
        "exp": datetime.utcnow() + timedelta(hours=1)
    }

    token = jwt.encode(
        data,
        os.environ.get("JWT_SECRET", "test-jwt-secret"),
        algorithm="HS256"
    )

    return token


@pytest.fixture
def auth_headers(test_user_token):
    """Standard auth headers for requests."""
    return {
        "Authorization": f"Bearer {test_user_token}",
        "Content-Type": "application/json"
    }


# ============================================================================
# Model Fixtures
# ============================================================================

@pytest.fixture
def test_workspace(test_db_session):
    """Create test workspace."""
    from app.models import Workspace

    workspace = Workspace(
        id="test-workspace-123",
        name="Test Workspace",
        created_at=datetime.utcnow()
    )

    test_db_session.add(workspace)
    test_db_session.commit()
    test_db_session.refresh(workspace)

    return workspace


@pytest.fixture
def test_user(test_db_session, test_workspace):
    """Create test user."""
    from app.models import User

    user = User(
        id="test-user-123",
        email="test@example.com",
        name="Test User",
        role="admin",
        workspace_id=test_workspace.id,
        created_at=datetime.utcnow()
    )

    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)

    return user


@pytest.fixture
def test_workspace_b(test_db_session):
    """Create second test workspace (for isolation tests)."""
    from app.models import Workspace

    workspace = Workspace(
        id="test-workspace-456",
        name="Test Workspace B",
        created_at=datetime.utcnow()
    )

    test_db_session.add(workspace)
    test_db_session.commit()
    test_db_session.refresh(workspace)

    return workspace


@pytest.fixture
def test_connection(test_db_session, test_workspace):
    """Create test connection (Google Ads)."""
    from app.models import Connection

    connection = Connection(
        id="test-connection-123",
        workspace_id=test_workspace.id,
        provider="google",
        external_account_id="1234567890",
        name="Test Google Ads Account",
        status="active",
        token="test-token-encrypted",
        connected_at=datetime.utcnow()
    )

    test_db_session.add(connection)
    test_db_session.commit()
    test_db_session.refresh(connection)

    return connection


# ============================================================================
# Service Fixtures
# ============================================================================

@pytest.fixture
def qa_service(test_db_session):
    """Create QA service with test database."""
    from app.services.semantic_qa_service import SemanticQAService

    service = SemanticQAService(test_db_session)

    # Mock external dependencies (translator no longer exists in v4.0)
    service.metric_service = Mock()

    return service


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_llm():
    """Mock OpenAI LLM client with configurable responses."""
    mock_client = MagicMock()

    # Default response
    default_response = {
        "metrics": ["roas"],
        "time_window": {"type": "last_n_days", "value": 7}
    }

    # Current response (mutable)
    current_response = default_response.copy()

    # Setup initial mock
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps(current_response)
    mock_client.chat.completions.create.return_value = mock_response

    # Add set_response method
    def set_response(response_dict):
        """Allow tests to customize LLM response."""
        mock_response.choices[0].message.content = json.dumps(response_dict)

    mock_client.set_response = set_response
    return mock_client


@pytest.fixture
def mock_metric_service():
    """Mock UnifiedMetricService."""
    mock_service = MagicMock()

    # Default metric response
    mock_result = {
        "summary": 3.5,
        "previous": 3.0,
        "delta_pct": 0.1667
    }

    mock_service.get_metric.return_value = mock_result

    return mock_service


@pytest.fixture
def mock_telemetry():
    """Mock TelemetryCollector."""
    mock_collector = MagicMock()
    mock_collector.events = []

    def track_event(event_type, **kwargs):
        mock_collector.events.append({"type": event_type, **kwargs})

    mock_collector.track_event = track_event

    return mock_collector


# ============================================================================
# Helper Fixtures
# ============================================================================

@pytest.fixture
def date_window():
    """Create date range for last 7 days."""
    now = datetime.utcnow()
    return {
        "start_date": now - timedelta(days=7),
        "end_date": now
    }


@pytest.fixture
def sample_compilation_result():
    """Create sample CompilationResult for visual testing."""
    from app.semantic.compiler import CompilationResult

    return CompilationResult(
        strategy="summary",
        metrics=["roas"],
        summary=Mock(
            metric_name="roas",
            value=3.5,
            previous=3.0,
            delta_pct=0.1667,
            unit="x"
        ),
        breakdown=None,
        entities=None,
        timeseries=None
    )


# ============================================================================
# Cleanup Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup(test_db_session):
    """Clean up test data with explicit FK dependency ordering."""
    yield

    try:
        # Import models at runtime to avoid circular imports
        from app.models import (
            QaQueryLog, Connection, User, Workspace, Token, Entity,
            MetricFact, ComputeRun, Pnl, ManualCost, Fetch, Import,
            WorkspaceMember, WorkspaceInvite, QaFeedback,
            ShopifyShop, ShopifyProduct, ShopifyCustomer, ShopifyOrder,
            ShopifyOrderLineItem, PixelEvent, CustomerJourney,
            JourneyTouchpoint, Attribution, AuthCredential
        )

        # Delete in order: Dependencies → Dependents
        # This prevents FK constraint violations

        # Layer 1: Bottom-level entities (no FK dependencies to other test models)
        test_db_session.query(QaQueryLog).delete()
        test_db_session.query(QaFeedback).delete()
        test_db_session.query(Token).delete()
        test_db_session.query(AuthCredential).delete()
        test_db_session.query(PixelEvent).delete()
        test_db_session.query(JourneyTouchpoint).delete()
        test_db_session.query(Attribution).delete()
        test_db_session.query(ShopifyOrderLineItem).delete()

        # Layer 2: Entities that depend on Workspace/User
        test_db_session.query(Connection).delete()
        test_db_session.query(Entity).delete()
        test_db_session.query(MetricFact).delete()
        test_db_session.query(ComputeRun).delete()
        test_db_session.query(Pnl).delete()
        test_db_session.query(ManualCost).delete()
        test_db_session.query(Fetch).delete()
        test_db_session.query(Import).delete()
        test_db_session.query(CustomerJourney).delete()
        test_db_session.query(ShopifyShop).delete()
        test_db_session.query(ShopifyProduct).delete()
        test_db_session.query(ShopifyCustomer).delete()
        test_db_session.query(ShopifyOrder).delete()

        # Layer 3: User and Member entities
        test_db_session.query(WorkspaceMember).delete()
        test_db_session.query(WorkspaceInvite).delete()
        test_db_session.query(User).delete()

        # Layer 4: Workspace (top level)
        test_db_session.query(Workspace).delete()

        test_db_session.commit()

    except Exception as e:
        # If anything goes wrong, rollback and re-raise
        test_db_session.rollback()
        raise


# ============================================================================
# Notes
# ============================================================================
#
# USAGE:
#
# # Basic HTTP test
# def test_get_question(client, auth_headers, test_workspace):
#     response = client.post(
#         f"/qa?workspace_id={test_workspace.id}",
#         json={"question": "What's my ROAS?"},
#         headers=auth_headers
#     )
#     assert response.status_code == 200
#
# # Database test
# def test_workspace_data(test_db_session, test_workspace):
#     metrics = test_db_session.query(MetricFact).filter_by(
#         workspace_id=test_workspace.id
#     ).all()
#     assert len(metrics) > 0
#
# # Service test
# def test_qa_service(qa_service, mock_llm):
#     qa_service.translator.to_semantic_query = Mock(return_value=semantic_query)
#     result = qa_service.answer_semantic("What's my ROAS?", workspace_id="test")
#     assert "answer" in result
#
# ============================================================================
