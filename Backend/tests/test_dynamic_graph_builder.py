import json
import os
import sys
import types
from unittest.mock import patch

from src.application.services.agent_registry_service import (
    AgentManifest,
    FileAgentRegistryRepository,
    AgentRegistryService,
)
from src.application.services.agent_config_service import AgentConfigService
from src.shared.agent_config_repository import FileAgentConfigRepository
from src.infrastructure.langgraph.dynamic_graph_builder import DynamicGraphBuilder


def test_agent_manifest_backfills_paths() -> None:
    manifest = AgentManifest(
        agent_name="legacy_agent",
        display_name="Legacy Agent",
        version="1.0.0",
        description="Legacy manifest",
        category="custom",
        supported_intents=["summary"],
        capabilities={},
        metadata={
            "agent_class_path": "legacy.module.Agent",
            "node_class_path": "legacy.module.Node",
            "enabled": False,
        },
    )
    assert manifest.agent_class_path == "legacy.module.Agent"
    assert manifest.node_class_path == "legacy.module.Node"
    assert manifest.enabled is False
    assert manifest.metadata["enabled"] is False

    manifest_no_enabled = AgentManifest(
        agent_name="new_agent",
        display_name="New Agent",
        version="1.0.0",
        description="New manifest",
        category="custom",
        supported_intents=["summary"],
        capabilities={},
        metadata={
            "agent_class_path": "pkg.Agent",
            "node_class_path": "pkg.Node",
        },
    )
    assert manifest_no_enabled.enabled is True
    assert manifest_no_enabled.metadata["enabled"] is True


def test_registry_repository_loads_legacy_payload(tmp_path) -> None:
    registry_path = tmp_path / "agents_registry.json"
    legacy_payload = {
        "legacy_agent": {
            "agent_name": "legacy_agent",
            "display_name": "Legacy Agent",
            "version": "1.0.0",
            "description": "Legacy manifest",
            "category": "custom",
            "supported_intents": ["summary"],
            "capabilities": {},
            "metadata": {
                "agent_class_path": "legacy.module.Agent",
                "node_class_path": "legacy.module.Node",
            },
        }
    }
    registry_path.write_text(json.dumps(legacy_payload), encoding="utf-8")

    repo = FileAgentRegistryRepository(registry_path=registry_path)
    manifests = repo.load_manifests()
    assert "legacy_agent" in manifests
    loaded = manifests["legacy_agent"]
    assert loaded.agent_class_path == "legacy.module.Agent"
    assert loaded.node_class_path == "legacy.module.Node"
    assert loaded.enabled is True
    assert loaded.metadata["enabled"] is True


def test_dynamic_graph_builder_rebuild_tracks_version(tmp_path) -> None:
    module_name = "tests.dynamic_dummy_module"
    module = types.ModuleType(module_name)
    code = """
from src.infrastructure.langgraph.nodes.base import GraphNode
from src.domain.agents.agent_protocol import BaseAgent
from src.domain.agents.agent_models import AgentTask, AgentResult, TaskStatus, IntentType


class DummyNode(GraphNode):
    def __init__(self, name: str):
        super().__init__(name=name)

    def run(self, state):
        return state


class DummyAgent(BaseAgent):
    @property
    def supported_intents(self):
        return [IntentType.SUMMARY_REQUEST]

    async def process(self, task: AgentTask) -> AgentResult:
        return AgentResult(
            task_id=task.task_id,
            agent_name=self.agent_name,
            status=TaskStatus.COMPLETED,
            data={},
        )
"""
    try:
        exec(code, module.__dict__)
        sys.modules[module_name] = module

        registry_path = tmp_path / "agents_registry.json"
        config_dir = tmp_path / "config"
        repo = FileAgentRegistryRepository(registry_path=registry_path)
        config_repo = FileAgentConfigRepository(base_dir=config_dir)
        config_service = AgentConfigService(config_repo)
        registry_service = AgentRegistryService(registry_repo=repo, config_service=config_service)

        manifest = AgentManifest(
            agent_name="dummy_agent",
            display_name="Dummy Agent",
            version="1.0.0",
            description="Test agent",
            category="custom",
            supported_intents=["summary"],
            capabilities={},
            metadata={
                "agent_class_path": f"{module_name}.DummyAgent",
                "node_class_path": f"{module_name}.DummyNode",
                "enabled": True,
            },
            agent_class_path=f"{module_name}.DummyAgent",
            node_class_path=f"{module_name}.DummyNode",
            enabled=True,
        )
        env_vars = {
            "SECRET_KEY": "test-secret-key-very-long-for-testing-purposes",
            "API_KEY_BACKEND": "test-api-key-backend",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            repo.save_manifest("dummy_agent", manifest)
            registry_service.refresh_registry()
            registry_service.config_service.set_enabled("dummy_agent", True)

            builder = DynamicGraphBuilder(registry_service)
            builder.build_dynamic(rebuild_reason="unit_test")
            info = builder.get_graph_info()
            assert info["version"] == 1
            assert "dummy_agent" in info["nodes"]
            assert "dummy_agent" in info["custom_agents"]

            builder.rebuild_with_new_agent("dummy_agent")
            info_after_register = builder.get_graph_info()
            assert info_after_register["version"] == 2
            assert info_after_register["rebuild_reason"] == "register_agent"

            repo.remove_manifest("dummy_agent")
            registry_service.refresh_registry()
            builder.remove_agent_from_graph("dummy_agent")
            info_after_remove = builder.get_graph_info()
            assert info_after_remove["version"] == 3
            assert info_after_remove["rebuild_reason"] == "unregister_agent"
            assert "dummy_agent" not in info_after_remove["nodes"]
            assert info_after_remove["registered_agents"] == []
            assert info_after_remove["has_current_graph"] is True
    finally:
        sys.modules.pop(module_name, None)








