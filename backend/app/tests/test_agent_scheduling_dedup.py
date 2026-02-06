import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    AccumulationModeEnum,
    AccumulationUnitEnum,
    Agent,
    AgentScopeTypeEnum,
    AgentStatusEnum,
    RoleEnum,
    TriggerModeEnum,
    User,
    Workspace,
)
from app.services.agents.evaluation_engine import AgentEvaluationEngine


def _setup_db(tmp_path):
    db_file = tmp_path / "agent_sched_claim.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return engine, SessionLocal


def _seed_agent(session, now: datetime) -> uuid.UUID:
    workspace_id = uuid.uuid4()
    user_id = uuid.uuid4()
    agent_id = uuid.uuid4()

    workspace = Workspace(id=workspace_id, name="Sched test")
    user = User(
        id=user_id,
        clerk_id=f"clerk-{user_id}",
        email=f"{user_id}@example.com",
        name="Sched User",
        role=RoleEnum.admin,
        workspace_id=workspace_id,
    )
    agent = Agent(
        id=agent_id,
        workspace_id=workspace_id,
        name=f"sched-{agent_id}",
        description="scheduled report",
        scope_type=AgentScopeTypeEnum.all,
        scope_config={"level": "campaign", "provider": "google", "aggregate": True},
        condition={"type": "threshold", "metric": "roas", "operator": "gt", "value": 0},
        accumulation_required=1,
        accumulation_unit=AccumulationUnitEnum.evaluations,
        accumulation_mode=AccumulationModeEnum.consecutive,
        accumulation_window=None,
        trigger_mode=TriggerModeEnum.once,
        cooldown_duration_minutes=60,
        continuous_interval_minutes=15,
        actions=[{"type": "notify", "channels": []}],
        safety_config=None,
        schedule_type="daily",
        schedule_config={
            "hour": now.hour,
            "minute": now.minute,
            "timezone": "UTC",
        },
        condition_required=False,
        date_range_type="yesterday",
        status=AgentStatusEnum.active,
        created_by=user_id,
    )
    session.add_all([workspace, user, agent])
    session.commit()
    return agent_id


def test_try_claim_scheduled_agent_run_is_atomic(tmp_path):
    engine, SessionLocal = _setup_db(tmp_path)
    now = datetime.now(timezone.utc)

    seed = SessionLocal()
    agent_id = _seed_agent(seed, now)
    seed.close()

    db1 = SessionLocal()
    db2 = SessionLocal()
    try:
        engine1 = AgentEvaluationEngine(db1)
        engine2 = AgentEvaluationEngine(db2)

        assert engine1._try_claim_scheduled_agent_run(agent_id, now) is True
        assert engine2._try_claim_scheduled_agent_run(agent_id, now) is False
    finally:
        db1.close()
        db2.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_should_run_handles_naive_last_scheduled_run_at(tmp_path):
    engine, SessionLocal = _setup_db(tmp_path)
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)

    seed = SessionLocal()
    agent_id = _seed_agent(seed, now)
    # Simulate a DB value without timezone info.
    agent = seed.query(Agent).filter(Agent.id == agent_id).one()
    agent.last_scheduled_run_at = datetime.utcnow()
    seed.commit()
    seed.close()

    db = SessionLocal()
    try:
        engine_obj = AgentEvaluationEngine(db)
        agent = db.query(Agent).filter(Agent.id == agent_id).one()
        should_run = engine_obj._should_run_scheduled_agent(agent, now)
        assert should_run is False
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
