"""Unit tests for Meta sync service critical paths."""

from types import SimpleNamespace
from uuid import uuid4

from app.models import LevelEnum, ProviderEnum
from app.services import meta_sync_service as svc


class _FakeQuery:
    def __init__(self, connection):
        self._connection = connection

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._connection


class _FakeDB:
    def __init__(self, connection):
        self._connection = connection
        self.committed = False

    def query(self, model):
        return _FakeQuery(self._connection)

    def commit(self):
        self.committed = True


class _FakeMetaClient:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.ads_requested_for = []

    def get_campaigns(self, account_id: str):
        return [{"id": "cmp-1", "name": "Campaign 1", "status": "ACTIVE"}]

    def get_adsets(self, campaign_id: str):
        return [
            {"id": "as-1", "name": "AdSet 1", "status": "ACTIVE"},
            {"id": "as-2", "name": "AdSet 2", "status": "ACTIVE"},
        ]

    def get_ads(self, adset_id: str):
        self.ads_requested_for.append(adset_id)
        if adset_id == "as-1":
            return [
                {"id": "ad-1", "name": "Ad 1", "status": "ACTIVE"},
                {"id": "ad-2", "name": "Ad 2", "status": "PAUSED"},
            ]
        if adset_id == "as-2":
            return [{"id": "ad-3", "name": "Ad 3", "status": "ACTIVE"}]
        return []

    def get_creative_details(self, creative_id: str):
        return None


class _FakeMetaClientActiveOnly:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.adsets_requested_for = []
        self.ads_requested_for = []

    def get_campaigns(self, account_id: str):
        return [
            {"id": "cmp-active", "name": "Active Campaign", "status": "ACTIVE"},
            {"id": "cmp-paused", "name": "Paused Campaign", "status": "PAUSED"},
        ]

    def get_adsets(self, campaign_id: str):
        self.adsets_requested_for.append(campaign_id)
        if campaign_id == "cmp-active":
            return [
                {"id": "as-active", "name": "Active AdSet", "status": "ACTIVE"},
                {"id": "as-paused", "name": "Paused AdSet", "status": "PAUSED"},
            ]
        return [{"id": "as-other", "name": "Other AdSet", "status": "ACTIVE"}]

    def get_ads(self, adset_id: str):
        self.ads_requested_for.append(adset_id)
        if adset_id == "as-active":
            return [
                {"id": "ad-active", "name": "Active Ad", "status": "ACTIVE"},
                {"id": "ad-paused", "name": "Paused Ad", "status": "PAUSED"},
            ]
        return [{"id": "ad-other", "name": "Other Ad", "status": "ACTIVE"}]

    def get_creative_details(self, creative_id: str):
        return None


def test_sync_meta_entities_fetches_ads_per_adset(monkeypatch):
    workspace_id = uuid4()
    connection_id = uuid4()

    connection = SimpleNamespace(
        id=connection_id,
        workspace_id=workspace_id,
        provider=ProviderEnum.meta,
        external_account_id="1234567890",
    )
    db = _FakeDB(connection)

    fake_client_holder = {}

    def _fake_client_factory(access_token: str):
        client = _FakeMetaClient(access_token)
        fake_client_holder["client"] = client
        return client

    adset_ids_to_entity_ids = {}
    ad_upserts = []

    def _fake_upsert_entity(
        db,
        connection,
        external_id,
        level,
        name,
        status,
        parent_id=None,
        goal=None,
        thumbnail_url=None,
        image_url=None,
        media_type=None,
        tracking_params=None,
    ):
        entity = SimpleNamespace(id=uuid4())
        if level == LevelEnum.adset:
            adset_ids_to_entity_ids[external_id] = entity.id
        if level == LevelEnum.ad:
            ad_upserts.append((external_id, parent_id))
        return entity, True

    monkeypatch.setattr(svc, "MetaAdsClient", _fake_client_factory)
    monkeypatch.setattr(svc, "_get_access_token", lambda conn: "test-token")
    monkeypatch.setattr(svc, "_upsert_entity", _fake_upsert_entity)

    result = svc.sync_meta_entities(
        db=db,
        workspace_id=workspace_id,
        connection_id=connection_id,
    )

    assert result.success is True
    assert db.committed is True
    assert result.synced.adsets_created == 2
    assert result.synced.ads_created == 3

    client = fake_client_holder["client"]
    assert client.ads_requested_for == ["as-1", "as-2"]

    # Ads must be linked to the matching adset entity id, not the last adset.
    expected_parent_ids = {
        "ad-1": adset_ids_to_entity_ids["as-1"],
        "ad-2": adset_ids_to_entity_ids["as-1"],
        "ad-3": adset_ids_to_entity_ids["as-2"],
    }
    for ad_external_id, parent_id in ad_upserts:
        assert parent_id == expected_parent_ids[ad_external_id]


def test_sync_meta_entities_active_only_filters_non_active(monkeypatch):
    workspace_id = uuid4()
    connection_id = uuid4()

    connection = SimpleNamespace(
        id=connection_id,
        workspace_id=workspace_id,
        provider=ProviderEnum.meta,
        external_account_id="1234567890",
    )
    db = _FakeDB(connection)

    fake_client_holder = {}

    def _fake_client_factory(access_token: str):
        client = _FakeMetaClientActiveOnly(access_token)
        fake_client_holder["client"] = client
        return client

    upserted_entities = []

    def _fake_upsert_entity(
        db,
        connection,
        external_id,
        level,
        name,
        status,
        parent_id=None,
        goal=None,
        thumbnail_url=None,
        image_url=None,
        media_type=None,
        tracking_params=None,
    ):
        upserted_entities.append((level, external_id))
        return SimpleNamespace(id=uuid4()), True

    monkeypatch.setattr(svc, "MetaAdsClient", _fake_client_factory)
    monkeypatch.setattr(svc, "_get_access_token", lambda conn: "test-token")
    monkeypatch.setattr(svc, "_upsert_entity", _fake_upsert_entity)

    result = svc.sync_meta_entities(
        db=db,
        workspace_id=workspace_id,
        connection_id=connection_id,
        entity_sync_mode="active_only",
    )

    assert result.success is True
    assert result.synced.campaigns_created == 1
    assert result.synced.adsets_created == 1
    assert result.synced.ads_created == 1

    client = fake_client_holder["client"]
    assert client.adsets_requested_for == ["cmp-active"]
    assert client.ads_requested_for == ["as-active"]

    assert upserted_entities == [
        (LevelEnum.campaign, "cmp-active"),
        (LevelEnum.adset, "as-active"),
        (LevelEnum.ad, "ad-active"),
    ]


def test_parse_actions_handles_meta_action_variants():
    insight = {
        "actions": [
            {"action_type": "purchase", "value": "2"},
            {"action_type": "omni_purchase", "value": "1"},
            {"action_type": "offsite_conversion.fb_pixel_purchase", "value": "3"},
            {"action_type": "lead", "value": "4"},
            {"action_type": "onsite_conversion.lead_grouped", "value": "1"},
            {"action_type": "app_install", "value": "2"},
            {"action_type": "mobile_app_install", "value": "1"},
            {"action_type": "purchase", "value": "not-a-number"},
        ],
        "action_values": [
            {"action_type": "purchase", "value": "10.5"},
            {"action_type": "omni_purchase", "value": "5"},
            {"action_type": "offsite_conversion.fb_pixel_purchase", "value": "2.5"},
        ],
    }

    parsed = svc._parse_actions(insight)

    assert parsed["purchases"] == 6.0
    assert parsed["leads"] == 5.0
    assert parsed["installs"] == 3
    assert parsed["purchase_value"] == 18.0
