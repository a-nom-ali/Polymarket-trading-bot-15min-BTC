"""
Tests for diff utilities.
"""

import pytest

from src.infrastructure.versioning.diff import (
    ChangeType,
    compute_diff,
    compute_dict_diff,
)
from src.infrastructure.versioning import EntityType


class TestDiff:
    """Tests for diff utilities"""

    def test_compute_diff_no_changes(self):
        """Test diff with identical data"""
        data = {"key": "value", "nested": {"a": 1}}

        diff = compute_diff(
            entity_type=EntityType.WORKFLOW,
            entity_id="test",
            from_version=1,
            to_version=2,
            from_data=data,
            to_data=data
        )

        assert len(diff.changes) == 0
        assert "0 additions" in diff.summary

    def test_compute_diff_addition(self):
        """Test diff with added key"""
        from_data = {"a": 1}
        to_data = {"a": 1, "b": 2}

        diff = compute_diff(
            entity_type=EntityType.CONFIG,
            entity_id="test",
            from_version=1,
            to_version=2,
            from_data=from_data,
            to_data=to_data
        )

        assert len(diff.changes) == 1
        assert diff.changes[0]["path"] == "b"
        assert diff.changes[0]["type"] == "add"
        assert diff.changes[0]["new"] == 2

    def test_compute_diff_removal(self):
        """Test diff with removed key"""
        from_data = {"a": 1, "b": 2}
        to_data = {"a": 1}

        diff = compute_diff(
            entity_type=EntityType.CONFIG,
            entity_id="test",
            from_version=1,
            to_version=2,
            from_data=from_data,
            to_data=to_data
        )

        assert len(diff.changes) == 1
        assert diff.changes[0]["path"] == "b"
        assert diff.changes[0]["type"] == "remove"
        assert diff.changes[0]["old"] == 2

    def test_compute_diff_modification(self):
        """Test diff with modified value"""
        from_data = {"a": 1}
        to_data = {"a": 2}

        diff = compute_diff(
            entity_type=EntityType.CONFIG,
            entity_id="test",
            from_version=1,
            to_version=2,
            from_data=from_data,
            to_data=to_data
        )

        assert len(diff.changes) == 1
        assert diff.changes[0]["path"] == "a"
        assert diff.changes[0]["type"] == "modify"
        assert diff.changes[0]["old"] == 1
        assert diff.changes[0]["new"] == 2

    def test_compute_diff_nested(self):
        """Test diff with nested objects"""
        from_data = {"config": {"level": 1, "enabled": True}}
        to_data = {"config": {"level": 2, "enabled": True}}

        diff = compute_diff(
            entity_type=EntityType.CONFIG,
            entity_id="test",
            from_version=1,
            to_version=2,
            from_data=from_data,
            to_data=to_data
        )

        assert len(diff.changes) == 1
        assert diff.changes[0]["path"] == "config.level"
        assert diff.changes[0]["old"] == 1
        assert diff.changes[0]["new"] == 2

    def test_compute_diff_list_change(self):
        """Test diff with list changes"""
        from_data = {"items": [1, 2, 3]}
        to_data = {"items": [1, 2, 3, 4]}

        diff = compute_diff(
            entity_type=EntityType.WORKFLOW,
            entity_id="test",
            from_version=1,
            to_version=2,
            from_data=from_data,
            to_data=to_data
        )

        assert len(diff.changes) == 1
        assert diff.changes[0]["path"] == "items"
        assert diff.changes[0]["type"] == "modify"

    def test_compute_diff_complex(self):
        """Test diff with multiple changes"""
        from_data = {
            "name": "old_name",
            "version": "1.0.0",
            "config": {"a": 1, "b": 2},
            "to_remove": "value"
        }
        to_data = {
            "name": "new_name",
            "version": "1.0.0",
            "config": {"a": 1, "b": 3},
            "new_key": "added"
        }

        diff = compute_diff(
            entity_type=EntityType.WORKFLOW,
            entity_id="test",
            from_version=1,
            to_version=2,
            from_data=from_data,
            to_data=to_data
        )

        # Should have: name modified, config.b modified, to_remove removed, new_key added
        assert len(diff.changes) == 4

        paths = [c["path"] for c in diff.changes]
        assert "name" in paths
        assert "config.b" in paths
        assert "to_remove" in paths
        assert "new_key" in paths

    def test_compute_dict_diff(self):
        """Test simple dict diff"""
        old = {"a": 1, "b": 2}
        new = {"a": 1, "b": 3, "c": 4}

        result = compute_dict_diff(old, new)

        assert result["change_count"] == 2
        assert len(result["changes"]) == 2

    def test_diff_summary(self):
        """Test diff summary generation"""
        from_data = {"a": 1}
        to_data = {"a": 2, "b": 3}

        diff = compute_diff(
            entity_type=EntityType.CONFIG,
            entity_id="test",
            from_version=1,
            to_version=2,
            from_data=from_data,
            to_data=to_data
        )

        assert "1 additions" in diff.summary
        assert "1 modifications" in diff.summary
        assert "0 removals" in diff.summary
