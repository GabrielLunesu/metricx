"""Regression tests for workspace deletion dependency ordering."""

from uuid import uuid4

from app.models import (
    Workspace,
    WorkspaceMember,
    User,
    Entity,
    Attribution,
    RoleEnum,
    LevelEnum,
)
from app.routers.workspaces import delete_workspace


def test_delete_workspace_removes_attributions_before_entities(test_db_session):
    workspace_to_delete = Workspace(id=uuid4(), name="Delete Me")
    workspace_keep = Workspace(id=uuid4(), name="Keep Me")

    user = User(
        id=uuid4(),
        email="owner-delete@example.com",
        name="Owner",
        role=RoleEnum.owner,
        # Keep active workspace outside the one being deleted so this test
        # focuses on deletion dependency ordering.
        workspace_id=workspace_keep.id,
    )

    member_delete = WorkspaceMember(
        id=uuid4(),
        workspace_id=workspace_to_delete.id,
        user_id=user.id,
        role=RoleEnum.owner,
        status="active",
    )
    member_keep = WorkspaceMember(
        id=uuid4(),
        workspace_id=workspace_keep.id,
        user_id=user.id,
        role=RoleEnum.admin,
        status="active",
    )

    entity = Entity(
        id=uuid4(),
        workspace_id=workspace_to_delete.id,
        level=LevelEnum.campaign,
        external_id="cmp-1",
        name="Campaign 1",
        status="ACTIVE",
    )

    attribution = Attribution(
        id=uuid4(),
        workspace_id=workspace_to_delete.id,
        entity_id=entity.id,
        provider="meta",
        entity_level="campaign",
        match_type="utm_source",
        confidence="high",
        attribution_model="last_click",
    )

    entity_id = entity.id
    attribution_id = attribution.id

    test_db_session.add_all(
        [
            workspace_to_delete,
            workspace_keep,
            user,
            member_delete,
            member_keep,
            entity,
            attribution,
        ]
    )
    test_db_session.commit()

    response = delete_workspace(
        workspace_id=workspace_to_delete.id,
        db=test_db_session,
        current_user=user,
    )

    assert response.detail == "Workspace deleted successfully"
    assert (
        test_db_session.query(Workspace)
        .filter(Workspace.id == workspace_to_delete.id)
        .first()
        is None
    )
    assert (
        test_db_session.query(Entity)
        .filter(Entity.id == entity_id)
        .first()
        is None
    )
    assert (
        test_db_session.query(Attribution)
        .filter(Attribution.id == attribution_id)
        .first()
        is None
    )

    test_db_session.refresh(user)
    assert user.workspace_id == workspace_keep.id
