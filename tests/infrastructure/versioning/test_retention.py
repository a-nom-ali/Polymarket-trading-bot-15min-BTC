"""
Tests for retention policy enforcement.
"""

import pytest
from datetime import datetime, timedelta

from src.infrastructure.versioning import EntityType, RetentionPolicy, VersionMetadata
from src.infrastructure.versioning.retention import apply_policy


class TestRetentionPolicy:
    """Tests for retention policy"""

    def _create_metadata(
        self,
        version: int,
        created_at: datetime = None,
        tags: list = None
    ) -> VersionMetadata:
        """Helper to create test metadata"""
        return VersionMetadata(
            entity_type=EntityType.BOT_STATE,
            entity_id="test",
            version=version,
            created_at=created_at or datetime.utcnow(),
            created_by="test",
            tags=tags or []
        )

    def test_keep_latest(self):
        """Test keep_latest always preserves N newest versions"""
        versions = [self._create_metadata(i) for i in range(10, 0, -1)]  # 10, 9, 8...

        policy = RetentionPolicy(keep_latest=5)
        to_delete = apply_policy(versions, policy)

        # Should keep 5 latest (versions 10-6), delete 5 oldest (versions 5-1)
        assert len(to_delete) == 0  # No max_versions or max_age set

    def test_max_versions(self):
        """Test max_versions limit"""
        versions = [self._create_metadata(i) for i in range(10, 0, -1)]

        policy = RetentionPolicy(max_versions=5, keep_latest=2)
        to_delete = apply_policy(versions, policy)

        # Keep 2 latest + 3 more = 5 total, delete 5
        assert len(to_delete) == 5

        # Verify we're deleting the oldest ones
        deleted_versions = {m.version for m in to_delete}
        assert 1 in deleted_versions
        assert 10 not in deleted_versions  # Latest kept

    def test_max_age(self):
        """Test max_age retention"""
        now = datetime.utcnow()
        old_time = now - timedelta(days=60)

        versions = [
            self._create_metadata(5, created_at=now),
            self._create_metadata(4, created_at=now - timedelta(days=10)),
            self._create_metadata(3, created_at=now - timedelta(days=30)),
            self._create_metadata(2, created_at=old_time),
            self._create_metadata(1, created_at=old_time - timedelta(days=30)),
        ]

        policy = RetentionPolicy(max_age=timedelta(days=45), keep_latest=1)
        to_delete = apply_policy(versions, policy)

        # Should delete versions older than 45 days
        deleted_versions = {m.version for m in to_delete}
        assert 1 in deleted_versions
        assert 2 in deleted_versions
        assert 5 not in deleted_versions  # Latest kept

    def test_keep_tagged(self):
        """Test keep_tagged preserves tagged versions"""
        versions = [
            self._create_metadata(5),
            self._create_metadata(4, tags=["important"]),
            self._create_metadata(3),
            self._create_metadata(2, tags=["release"]),
            self._create_metadata(1),
        ]

        policy = RetentionPolicy(max_versions=2, keep_latest=1, keep_tagged=True)
        to_delete = apply_policy(versions, policy)

        # Should keep: v5 (latest), v4 (tagged), v2 (tagged)
        # Should delete: v3, v1
        deleted_versions = {m.version for m in to_delete}
        assert 4 not in deleted_versions  # Tagged
        assert 2 not in deleted_versions  # Tagged
        assert 5 not in deleted_versions  # Latest

    def test_keep_tagged_disabled(self):
        """Test keep_tagged=False doesn't preserve tagged versions"""
        versions = [
            self._create_metadata(3),
            self._create_metadata(2, tags=["release"]),
            self._create_metadata(1),
        ]

        policy = RetentionPolicy(max_versions=1, keep_latest=1, keep_tagged=False)
        to_delete = apply_policy(versions, policy)

        # Tagged version 2 should be deleted
        deleted_versions = {m.version for m in to_delete}
        assert 2 in deleted_versions

    def test_empty_versions(self):
        """Test with empty versions list"""
        policy = RetentionPolicy(max_versions=10)
        to_delete = apply_policy([], policy)

        assert len(to_delete) == 0

    def test_combined_policies(self):
        """Test combination of max_versions and max_age"""
        now = datetime.utcnow()

        versions = [
            self._create_metadata(10, created_at=now),
            self._create_metadata(9, created_at=now - timedelta(days=5)),
            self._create_metadata(8, created_at=now - timedelta(days=10)),
            self._create_metadata(7, created_at=now - timedelta(days=20)),
            self._create_metadata(6, created_at=now - timedelta(days=25)),
            self._create_metadata(5, created_at=now - timedelta(days=35)),  # Old
            self._create_metadata(4, created_at=now - timedelta(days=40)),  # Old
        ]

        policy = RetentionPolicy(
            max_versions=5,
            max_age=timedelta(days=30),
            keep_latest=2
        )
        to_delete = apply_policy(versions, policy)

        # Versions 5 and 4 are older than 30 days
        deleted_versions = {m.version for m in to_delete}
        assert 5 in deleted_versions
        assert 4 in deleted_versions
        assert 10 not in deleted_versions  # Latest
        assert 9 not in deleted_versions  # Second latest

    def test_all_versions_kept(self):
        """Test when all versions should be kept"""
        versions = [self._create_metadata(i) for i in range(3, 0, -1)]

        policy = RetentionPolicy(
            max_versions=10,
            keep_latest=5
        )
        to_delete = apply_policy(versions, policy)

        assert len(to_delete) == 0
