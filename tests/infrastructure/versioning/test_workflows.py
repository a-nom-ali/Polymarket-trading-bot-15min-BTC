"""
Tests for WorkflowVersionManager.
"""

import pytest

from src.infrastructure.versioning import create_version_store
from src.infrastructure.versioning.workflows import WorkflowVersionManager


class TestWorkflowVersionManager:
    """Tests for WorkflowVersionManager"""

    @pytest.fixture
    async def manager(self):
        store = create_version_store("memory")
        manager = WorkflowVersionManager(store)
        yield manager
        await store.close()

    @pytest.mark.asyncio
    async def test_save_workflow(self, manager: WorkflowVersionManager):
        """Test saving a workflow"""
        workflow = {
            "name": "Test Workflow",
            "version": "1.0.0",
            "blocks": [
                {"id": "block1", "category": "trigger", "type": "price_check"}
            ],
            "connections": []
        }

        meta = await manager.save_workflow(
            workflow_id="test_wf",
            workflow=workflow,
            created_by="user@example.com",
            message="Initial version"
        )

        assert meta.version == 1
        assert meta.entity_id == "test_wf"

    @pytest.mark.asyncio
    async def test_get_workflow(self, manager: WorkflowVersionManager):
        """Test getting a workflow"""
        workflow = {
            "name": "Get Test",
            "version": "1.0.0",
            "blocks": [],
            "connections": []
        }

        await manager.save_workflow("get_test", workflow, "test")

        result = await manager.get_workflow("get_test")

        assert result is not None
        assert result["name"] == "Get Test"

    @pytest.mark.asyncio
    async def test_get_specific_version(self, manager: WorkflowVersionManager):
        """Test getting a specific workflow version"""
        for i in range(3):
            workflow = {
                "name": f"Version {i+1}",
                "version": "1.0.0",
                "blocks": [],
                "connections": []
            }
            await manager.save_workflow("versioned", workflow, "test")

        v2 = await manager.get_workflow("versioned", version=2)
        assert v2["name"] == "Version 2"

    @pytest.mark.asyncio
    async def test_list_versions(self, manager: WorkflowVersionManager):
        """Test listing workflow versions"""
        for i in range(5):
            workflow = {
                "name": f"V{i+1}",
                "version": "1.0.0",
                "blocks": [],
                "connections": []
            }
            await manager.save_workflow("list_test", workflow, "test")

        versions = await manager.list_workflow_versions("list_test")

        assert len(versions) == 5
        assert versions[0].version == 5  # Newest first

    @pytest.mark.asyncio
    async def test_restore_workflow(self, manager: WorkflowVersionManager):
        """Test restoring a workflow to previous version"""
        # Create initial version
        await manager.save_workflow(
            "restore_test",
            {"name": "V1", "version": "1.0.0", "blocks": [], "connections": []},
            "test"
        )

        # Create second version
        await manager.save_workflow(
            "restore_test",
            {"name": "V2", "version": "1.0.0", "blocks": [], "connections": []},
            "test"
        )

        # Restore to version 1
        meta = await manager.restore_workflow("restore_test", 1, "admin")

        assert meta.version == 3  # New version created

        current = await manager.get_workflow("restore_test")
        assert current["name"] == "V1"

    @pytest.mark.asyncio
    async def test_diff_workflows(self, manager: WorkflowVersionManager):
        """Test diffing workflow versions"""
        await manager.save_workflow(
            "diff_test",
            {"name": "Old", "version": "1.0.0", "blocks": [], "connections": []},
            "test"
        )
        await manager.save_workflow(
            "diff_test",
            {"name": "New", "version": "1.0.0", "blocks": [], "connections": []},
            "test"
        )

        diff = await manager.diff_workflows("diff_test", 1, 2)

        assert diff is not None
        assert len(diff.changes) > 0

    def test_validate_workflow_valid(self, manager: WorkflowVersionManager):
        """Test validation of valid workflow"""
        workflow = {
            "name": "Valid Workflow",
            "version": "1.0.0",
            "blocks": [
                {"id": "b1", "category": "trigger"},
                {"id": "b2", "category": "action"}
            ],
            "connections": [
                {"from": {"blockId": "b1"}, "to": {"blockId": "b2"}}
            ]
        }

        errors = manager.validate_workflow(workflow)
        assert len(errors) == 0

    def test_validate_workflow_missing_fields(self, manager: WorkflowVersionManager):
        """Test validation catches missing fields"""
        workflow = {"name": "Incomplete"}

        errors = manager.validate_workflow(workflow)

        assert len(errors) > 0
        assert any("blocks" in e for e in errors)
        assert any("connections" in e for e in errors)
        assert any("version" in e for e in errors)

    def test_validate_workflow_invalid_connection(self, manager: WorkflowVersionManager):
        """Test validation catches invalid connections"""
        workflow = {
            "name": "Bad Connections",
            "version": "1.0.0",
            "blocks": [{"id": "b1", "category": "trigger"}],
            "connections": [
                {"from": {"blockId": "b1"}, "to": {"blockId": "nonexistent"}}
            ]
        }

        errors = manager.validate_workflow(workflow)

        assert len(errors) > 0
        assert any("nonexistent" in e for e in errors)

    def test_validate_workflow_missing_block_fields(self, manager: WorkflowVersionManager):
        """Test validation catches missing block fields"""
        workflow = {
            "name": "Bad Blocks",
            "version": "1.0.0",
            "blocks": [
                {"id": "b1"},  # Missing category
                {"category": "action"}  # Missing id
            ],
            "connections": []
        }

        errors = manager.validate_workflow(workflow)

        assert len(errors) >= 2

    @pytest.mark.asyncio
    async def test_save_invalid_workflow(self, manager: WorkflowVersionManager):
        """Test saving invalid workflow raises error"""
        invalid = {"name": "Invalid"}

        with pytest.raises(ValueError) as exc:
            await manager.save_workflow("invalid", invalid, "test")

        assert "validation failed" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_save_without_validation(self, manager: WorkflowVersionManager):
        """Test saving workflow without validation"""
        invalid = {"name": "No Validate", "custom": "data"}

        # Should not raise when validation disabled
        meta = await manager.save_workflow(
            "no_validate",
            invalid,
            "test",
            validate=False
        )

        assert meta.version == 1

    @pytest.mark.asyncio
    async def test_auto_version_field(self, manager: WorkflowVersionManager):
        """Test version field is auto-added if missing"""
        workflow = {
            "name": "Auto Version",
            "blocks": [],
            "connections": []
        }

        # Should auto-add version field
        await manager.save_workflow("auto_version", workflow, "test", validate=False)

        result = await manager.get_workflow("auto_version")
        assert result["version"] == "1.0.0"
