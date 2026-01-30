"""
Tests for VersionStore implementations.

Tests both InMemoryVersionStore and RedisVersionStore using a shared test suite.
"""

import pytest
from datetime import timedelta

from src.infrastructure.versioning import (
    create_version_store,
    EntityType,
    RetentionPolicy,
    VersionStore,
)


class VersionStoreTestSuite:
    """Base test suite for version store implementations"""

    @pytest.mark.asyncio
    async def test_save_and_get_version(self, store: VersionStore):
        """Test basic save and get operations"""
        meta = await store.save_version(
            entity_type=EntityType.WORKFLOW,
            entity_id="test_workflow",
            data={"name": "Test", "blocks": []},
            created_by="test_user",
            message="Initial version"
        )

        assert meta.version == 1
        assert meta.entity_id == "test_workflow"
        assert meta.entity_type == EntityType.WORKFLOW
        assert meta.created_by == "test_user"
        assert meta.message == "Initial version"

        snapshot = await store.get_version(
            EntityType.WORKFLOW, "test_workflow", 1
        )

        assert snapshot is not None
        assert snapshot.data["name"] == "Test"
        assert snapshot.metadata.version == 1

    @pytest.mark.asyncio
    async def test_version_incrementing(self, store: VersionStore):
        """Test version numbers increment correctly"""
        for i in range(3):
            meta = await store.save_version(
                entity_type=EntityType.WORKFLOW,
                entity_id="inc_test",
                data={"version": i},
                created_by="test"
            )
            assert meta.version == i + 1

    @pytest.mark.asyncio
    async def test_get_latest_version(self, store: VersionStore):
        """Test getting latest version"""
        for i in range(5):
            await store.save_version(
                entity_type=EntityType.STRATEGY,
                entity_id="latest_test",
                data={"iteration": i},
                created_by="test"
            )

        # Get without specifying version (should return latest)
        snapshot = await store.get_version(
            EntityType.STRATEGY, "latest_test"
        )

        assert snapshot is not None
        assert snapshot.data["iteration"] == 4
        assert snapshot.metadata.version == 5

        # Also test get_latest_version method
        latest = await store.get_latest_version(
            EntityType.STRATEGY, "latest_test"
        )
        assert latest == 5

    @pytest.mark.asyncio
    async def test_get_specific_version(self, store: VersionStore):
        """Test getting a specific version"""
        for i in range(5):
            await store.save_version(
                entity_type=EntityType.CONFIG,
                entity_id="specific_test",
                data={"value": i * 10},
                created_by="test"
            )

        # Get version 3
        snapshot = await store.get_version(
            EntityType.CONFIG, "specific_test", 3
        )

        assert snapshot is not None
        assert snapshot.data["value"] == 20  # i=2, so 2*10=20
        assert snapshot.metadata.version == 3

    @pytest.mark.asyncio
    async def test_list_versions(self, store: VersionStore):
        """Test listing version history"""
        for i in range(10):
            await store.save_version(
                entity_type=EntityType.CONFIG,
                entity_id="list_test",
                data={"n": i},
                created_by="test"
            )

        versions = await store.list_versions(
            EntityType.CONFIG, "list_test", limit=5
        )

        assert len(versions) == 5
        assert versions[0].version == 10  # Newest first
        assert versions[4].version == 6

    @pytest.mark.asyncio
    async def test_list_versions_with_offset(self, store: VersionStore):
        """Test listing versions with pagination"""
        for i in range(10):
            await store.save_version(
                entity_type=EntityType.WORKFLOW,
                entity_id="pagination_test",
                data={"n": i},
                created_by="test"
            )

        # Get second page
        versions = await store.list_versions(
            EntityType.WORKFLOW, "pagination_test", limit=3, offset=3
        )

        assert len(versions) == 3
        assert versions[0].version == 7  # Versions 7, 6, 5
        assert versions[2].version == 5

    @pytest.mark.asyncio
    async def test_delete_version(self, store: VersionStore):
        """Test deleting a version"""
        for i in range(3):
            await store.save_version(
                entity_type=EntityType.BOT_STATE,
                entity_id="delete_test",
                data={"n": i},
                created_by="test"
            )

        # Delete version 2
        deleted = await store.delete_version(
            EntityType.BOT_STATE, "delete_test", 2
        )
        assert deleted is True

        # Verify it's gone
        snapshot = await store.get_version(
            EntityType.BOT_STATE, "delete_test", 2
        )
        assert snapshot is None

        # Other versions should still exist
        snapshot = await store.get_version(
            EntityType.BOT_STATE, "delete_test", 1
        )
        assert snapshot is not None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_version(self, store: VersionStore):
        """Test deleting a version that doesn't exist"""
        deleted = await store.delete_version(
            EntityType.WORKFLOW, "nonexistent", 999
        )
        assert deleted is False

    @pytest.mark.asyncio
    async def test_rollback(self, store: VersionStore):
        """Test rollback creates new version with old data"""
        await store.save_version(
            entity_type=EntityType.WORKFLOW,
            entity_id="rollback_test",
            data={"state": "v1"},
            created_by="test"
        )
        await store.save_version(
            entity_type=EntityType.WORKFLOW,
            entity_id="rollback_test",
            data={"state": "v2"},
            created_by="test"
        )

        meta = await store.rollback(
            EntityType.WORKFLOW,
            "rollback_test",
            to_version=1,
            created_by="admin"
        )

        assert meta is not None
        assert meta.version == 3  # New version created
        assert "rollback" in meta.tags

        snapshot = await store.get_version(
            EntityType.WORKFLOW, "rollback_test"
        )
        assert snapshot.data["state"] == "v1"

    @pytest.mark.asyncio
    async def test_rollback_nonexistent_version(self, store: VersionStore):
        """Test rollback to nonexistent version"""
        meta = await store.rollback(
            EntityType.WORKFLOW,
            "nonexistent",
            to_version=999,
            created_by="admin"
        )
        assert meta is None

    @pytest.mark.asyncio
    async def test_tags(self, store: VersionStore):
        """Test saving versions with tags"""
        meta = await store.save_version(
            entity_type=EntityType.CONFIG,
            entity_id="tags_test",
            data={"config": "value"},
            created_by="test",
            tags=["release", "v1.0"]
        )

        assert "release" in meta.tags
        assert "v1.0" in meta.tags

        # Verify tags are persisted
        snapshot = await store.get_version(
            EntityType.CONFIG, "tags_test", 1
        )
        assert "release" in snapshot.metadata.tags

    @pytest.mark.asyncio
    async def test_checksum(self, store: VersionStore):
        """Test checksum is computed"""
        meta = await store.save_version(
            entity_type=EntityType.WORKFLOW,
            entity_id="checksum_test",
            data={"key": "value"},
            created_by="test"
        )

        assert meta.checksum is not None
        assert len(meta.checksum) == 16  # SHA-256 truncated to 16 chars

    @pytest.mark.asyncio
    async def test_parent_version(self, store: VersionStore):
        """Test parent version tracking"""
        meta1 = await store.save_version(
            entity_type=EntityType.STRATEGY,
            entity_id="parent_test",
            data={"v": 1},
            created_by="test"
        )
        assert meta1.parent_version is None  # First version has no parent

        meta2 = await store.save_version(
            entity_type=EntityType.STRATEGY,
            entity_id="parent_test",
            data={"v": 2},
            created_by="test"
        )
        assert meta2.parent_version == 1

    @pytest.mark.asyncio
    async def test_retention_policy_max_versions(self, store: VersionStore):
        """Test retention policy with max versions"""
        for i in range(20):
            await store.save_version(
                entity_type=EntityType.BOT_STATE,
                entity_id="retention_test",
                data={"n": i},
                created_by="test"
            )

        policy = RetentionPolicy(
            max_versions=10,
            keep_latest=5
        )

        deleted = await store.apply_retention_policy(
            EntityType.BOT_STATE,
            "retention_test",
            policy
        )

        assert deleted == 10  # Kept 10, deleted 10

        versions = await store.list_versions(
            EntityType.BOT_STATE, "retention_test", limit=100
        )
        assert len(versions) == 10

    @pytest.mark.asyncio
    async def test_get_nonexistent_entity(self, store: VersionStore):
        """Test getting version for nonexistent entity"""
        snapshot = await store.get_version(
            EntityType.WORKFLOW, "nonexistent_entity"
        )
        assert snapshot is None

        latest = await store.get_latest_version(
            EntityType.WORKFLOW, "nonexistent_entity"
        )
        assert latest is None

    @pytest.mark.asyncio
    async def test_different_entity_types(self, store: VersionStore):
        """Test same ID with different entity types"""
        await store.save_version(
            entity_type=EntityType.WORKFLOW,
            entity_id="same_id",
            data={"type": "workflow"},
            created_by="test"
        )
        await store.save_version(
            entity_type=EntityType.STRATEGY,
            entity_id="same_id",
            data={"type": "strategy"},
            created_by="test"
        )

        workflow = await store.get_version(EntityType.WORKFLOW, "same_id")
        strategy = await store.get_version(EntityType.STRATEGY, "same_id")

        assert workflow.data["type"] == "workflow"
        assert strategy.data["type"] == "strategy"


class TestInMemoryVersionStore(VersionStoreTestSuite):
    """Tests for InMemoryVersionStore"""

    @pytest.fixture
    async def store(self):
        store = create_version_store("memory")
        yield store
        await store.close()

    @pytest.mark.asyncio
    async def test_clear(self, store):
        """Test clearing all data"""
        from src.infrastructure.versioning.memory import InMemoryVersionStore
        assert isinstance(store, InMemoryVersionStore)

        await store.save_version(
            entity_type=EntityType.WORKFLOW,
            entity_id="clear_test",
            data={"data": "test"},
            created_by="test"
        )

        await store.clear()

        snapshot = await store.get_version(
            EntityType.WORKFLOW, "clear_test"
        )
        assert snapshot is None

    @pytest.mark.asyncio
    async def test_count_versions(self, store):
        """Test counting versions"""
        from src.infrastructure.versioning.memory import InMemoryVersionStore
        assert isinstance(store, InMemoryVersionStore)

        for i in range(5):
            await store.save_version(
                entity_type=EntityType.CONFIG,
                entity_id="count_test",
                data={"n": i},
                created_by="test"
            )

        count = await store.count_versions(EntityType.CONFIG, "count_test")
        assert count == 5


class TestRedisVersionStore:
    """Tests for RedisVersionStore (skipped if Redis unavailable)"""

    @pytest.fixture
    async def store(self):
        try:
            store = create_version_store("redis", url="redis://localhost:6379/15")
            # Test connection
            from src.infrastructure.versioning.redis_store import RedisVersionStore
            assert isinstance(store, RedisVersionStore)
            if not await store.ping():
                pytest.skip("Redis not available")

            # Clean up test database
            await store._ensure_connected()
            await store._redis.flushdb()

            yield store
            await store.close()
        except Exception as e:
            pytest.skip(f"Redis not available: {e}")

    @pytest.mark.asyncio
    async def test_basic_operations(self, store):
        """Basic Redis store test"""
        meta = await store.save_version(
            entity_type=EntityType.WORKFLOW,
            entity_id="redis_test",
            data={"test": "data"},
            created_by="test"
        )

        assert meta.version == 1

        snapshot = await store.get_version(
            EntityType.WORKFLOW, "redis_test"
        )
        assert snapshot.data["test"] == "data"

    @pytest.mark.asyncio
    async def test_tag_version(self, store):
        """Test adding tags to existing version"""
        await store.save_version(
            entity_type=EntityType.CONFIG,
            entity_id="tag_test",
            data={"config": "value"},
            created_by="test"
        )

        success = await store.tag_version(
            EntityType.CONFIG, "tag_test", 1, ["important", "backup"]
        )
        assert success is True

        snapshot = await store.get_version(
            EntityType.CONFIG, "tag_test", 1
        )
        assert "important" in snapshot.metadata.tags
        assert "backup" in snapshot.metadata.tags
