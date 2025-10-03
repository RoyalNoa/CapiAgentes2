#!/usr/bin/env python3
"""
CAPI - Agent Registry Service
=============================
Ruta: /Backend/src/application/services/agent_registry_service.py
Descripción: Servicio para registro dinámico de agentes en el sistema
Estado: ✅ NUEVO - Sistema de alta dinámico de agentes
Dependencias: AgentConfigService, LangGraph GraphBuilder
Propósito: Permitir registro dinámico de nuevos agentes sin restartar sistema
Patrón: Service Layer + Registry Pattern
"""

from __future__ import annotations

import json
import importlib
import inspect
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Dict, List, Any, Optional, Type, Protocol
from datetime import datetime, timedelta

from src.core.logging import get_logger
from src.application.services.agent_config_service import AgentConfigService
from src.domain.agents.agent_protocol import BaseAgent, IntentType

logger = get_logger(__name__)


@dataclass
class AgentManifest:
    """Manifiesto de un agente para registro dinámico."""

    agent_name: str
    display_name: str
    version: str
    description: str
    category: str
    supported_intents: List[str]
    capabilities: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    agent_class_path: str = ""
    node_class_path: str = ""
    author: str = "System"
    created_at: str = ""
    enabled: bool = True

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.agent_class_path:
            self.agent_class_path = str(self.metadata.get("agent_class_path", "") or "")
        if not self.node_class_path:
            self.node_class_path = str(self.metadata.get("node_class_path", "") or "")
        if "agent_class_path" not in self.metadata and self.agent_class_path:
            self.metadata["agent_class_path"] = self.agent_class_path
        if "node_class_path" not in self.metadata and self.node_class_path:
            self.metadata["node_class_path"] = self.node_class_path
        if "enabled" in self.metadata and self.metadata["enabled"] is not None:
            self.enabled = bool(self.metadata["enabled"])
        else:
            self.metadata.setdefault("enabled", self.enabled)


@dataclass
class AgentRegistrationRequest:
    """Request para registrar un nuevo agente"""
    agent_name: str
    display_name: str
    description: str
    agent_class_path: str  # e.g., "ia_workspace.agentes.mi_agente.handler.MiAgente"
    node_class_path: str   # e.g., "Backend.src.infrastructure.langgraph.nodes.mi_agente_node.MiAgenteNode"
    supported_intents: List[str]
    capabilities: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    enabled: bool = True


class AgentRegistryRepository(Protocol):
    """Port for persisting agent registry information."""

    def load_manifests(self) -> Dict[str, AgentManifest]:
        ...

    def save_manifest(self, agent_name: str, manifest: AgentManifest) -> None:
        ...

    def remove_manifest(self, agent_name: str) -> bool:
        ...


class FileAgentRegistryRepository:
    """File-based implementation of agent registry repository"""

    def __init__(self, registry_path: Optional[Path] = None):
        # Anchor to Backend/ia_workspace/data by resolving relative to this file location
        if registry_path is None:
            current_dir = Path(__file__).resolve().parent
            backend_root = current_dir.parents[2]  # Backend/
            self.registry_path = backend_root / "ia_workspace" / "data" / "agents_registry.json"
        else:
            self.registry_path = Path(registry_path)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

    def load_manifests(self) -> Dict[str, AgentManifest]:
        """Load all agent manifests from storage"""
        try:
            if not self.registry_path.exists():
                return {}

            with open(self.registry_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)

            manifests: Dict[str, AgentManifest] = {}
            for name, manifest_data in (raw_data or {}).items():
                manifest_dict = dict(manifest_data or {})
                metadata = manifest_dict.get("metadata") or {}
                manifest_dict.setdefault("capabilities", {})
                manifest_dict["metadata"] = metadata
                manifest_dict.setdefault("agent_class_path", metadata.get("agent_class_path", ""))
                manifest_dict.setdefault("node_class_path", metadata.get("node_class_path", ""))
                if "enabled" not in manifest_dict:
                    manifest_dict["enabled"] = metadata.get("enabled", True)
                try:
                    manifests[name] = AgentManifest(**manifest_dict)
                except TypeError as exc:
                    logger.error(f"Error parsing agent manifest {name}: {exc}")
            return manifests
        except Exception as e:
            logger.error(f"Error loading agent manifests: {e}")
            return {}

    def save_manifest(self, agent_name: str, manifest: AgentManifest) -> None:
        """Save agent manifest to storage"""
        try:
            manifests = self.load_manifests()
            manifests[agent_name] = manifest

            # Convert to dict format for JSON serialization
            data = {name: asdict(manifest) for name, manifest in manifests.items()}

            with open(self.registry_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Agent manifest saved: {agent_name}")
        except Exception as e:
            logger.error(f"Error saving agent manifest {agent_name}: {e}")
            raise

    def remove_manifest(self, agent_name: str) -> bool:
        """Remove agent manifest from storage"""
        try:
            manifests = self.load_manifests()
            if agent_name in manifests:
                del manifests[agent_name]

                # Save updated manifests
                data = {name: asdict(manifest) for name, manifest in manifests.items()}
                with open(self.registry_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                logger.info(f"Agent manifest removed: {agent_name}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error removing agent manifest {agent_name}: {e}")
            return False


class AgentRegistryService:
    """Servicio para registro dinámico de agentes"""

    def __init__(self,
                 registry_repo: AgentRegistryRepository,
                 config_service: AgentConfigService):
        self.registry_repo = registry_repo
        self.config_service = config_service
        self._registered_agents: Dict[str, AgentManifest] = {}
        self._load_existing_agents()

    def _load_existing_agents(self):
        """Carga agentes existentes del registro"""
        try:
            self._registered_agents = self.registry_repo.load_manifests()
            logger.info(f"Loaded {len(self._registered_agents)} registered agents")
        except Exception as e:
            logger.error(f"Error loading existing agents: {e}")
            self._registered_agents = {}

    def register_agent(self, request: AgentRegistrationRequest) -> bool:
        """
        Registra un nuevo agente en el sistema

        Returns:
            bool: True si el registro fue exitoso
        """
        try:
            logger.info(f"Starting agent registration: {request.agent_name}")

            # 1. Validar que el agente no existe (nombre único)
            if request.agent_name in self._registered_agents:
                raise ValueError(f"Agent with name '{request.agent_name}' is already registered")

            # 2. Validar que el display_name no existe (display_name único)
            existing_display_names = {
                manifest.display_name.lower(): manifest.agent_name
                for manifest in self._registered_agents.values()
            }
            if request.display_name.lower() in existing_display_names:
                existing_agent = existing_display_names[request.display_name.lower()]
                raise ValueError(f"Agent with display name '{request.display_name}' already exists (registered as '{existing_agent}')")

            # 3. Validar que los paths de clases no están duplicados
            existing_agent_paths: Dict[str, str] = {}
            existing_node_paths: Dict[str, str] = {}
            for manifest in self._registered_agents.values():
                agent_path = manifest.agent_class_path or manifest.metadata.get("agent_class_path", "")
                node_path = manifest.node_class_path or manifest.metadata.get("node_class_path", "")
                if agent_path:
                    existing_agent_paths[agent_path] = manifest.agent_name
                if node_path:
                    existing_node_paths[node_path] = manifest.agent_name

            if request.agent_class_path in existing_agent_paths:
                existing_agent = existing_agent_paths[request.agent_class_path]
                raise ValueError(f"Agent class path '{request.agent_class_path}' is already used by agent '{existing_agent}'")

            if request.node_class_path in existing_node_paths:
                existing_agent = existing_node_paths[request.node_class_path]
                raise ValueError(f"Node class path '{request.node_class_path}' is already used by agent '{existing_agent}'")

            # 4. Validar que las clases existen y son válidas
            self._validate_agent_classes(request)

            # 3. Crear manifiesto del agente
            manifest = AgentManifest(
                agent_name=request.agent_name,
                display_name=request.display_name,
                version="1.0.0",
                description=request.description,
                category="custom",
                supported_intents=request.supported_intents,
                capabilities=request.capabilities or {},
                metadata={
                    **(request.metadata or {}),
                    "agent_class_path": request.agent_class_path,
                    "node_class_path": request.node_class_path,
                    "registered_at": datetime.now().isoformat(),
                    "enabled": request.enabled,
                },
                agent_class_path=request.agent_class_path,
                node_class_path=request.node_class_path,
                enabled=request.enabled,
            )

            # 4. Guardar manifiesto
            self.registry_repo.save_manifest(request.agent_name, manifest)

            # 5. Actualizar cache local
            self._registered_agents[request.agent_name] = manifest

            # 6. Registrar en configuración con el estado solicitado
            self.config_service.set_enabled(request.agent_name, request.enabled)

            logger.info(f"Agent {request.agent_name} registered successfully")
            return True

        except Exception as e:
            logger.error(f"Error registering agent {request.agent_name}: {e}")
            raise

    def _validate_agent_classes(self, request: AgentRegistrationRequest):
        """Valida que las clases del agente existan y sean válidas"""
        try:
            # Validar agent class
            agent_module_path, agent_class_name = request.agent_class_path.rsplit('.', 1)
            agent_module = importlib.import_module(agent_module_path)
            agent_class = getattr(agent_module, agent_class_name)

            # Verificar que hereda de BaseAgent
            if not issubclass(agent_class, BaseAgent):
                raise ValueError(f"Agent class must inherit from BaseAgent")

            # Validar node class
            node_module_path, node_class_name = request.node_class_path.rsplit('.', 1)
            node_module = importlib.import_module(node_module_path)
            node_class = getattr(node_module, node_class_name)

            # Verificar que tiene método run
            if not hasattr(node_class, 'run'):
                raise ValueError(f"Node class must have 'run' method")

            logger.debug(f"Agent classes validated: {request.agent_name}")

        except ImportError as e:
            raise ValueError(f"Could not import agent classes: {e}")
        except AttributeError as e:
            raise ValueError(f"Agent class not found: {e}")

    def unregister_agent(self, agent_name: str) -> bool:
        """
        Desregistra un agente del sistema

        Returns:
            bool: True si el desregistro fue exitoso
        """
        try:
            if agent_name not in self._registered_agents:
                logger.warning(f"Agent {agent_name} not found in registry")
                return False

            # 1. Remover del registro
            success = self.registry_repo.remove_manifest(agent_name)

            if success:
                # 2. Remover del cache local
                del self._registered_agents[agent_name]

                # 3. Deshabilitar en configuración
                self.config_service.set_enabled(agent_name, False)

                logger.info(f"Agent {agent_name} unregistered successfully")
                return True

            return False

        except Exception as e:
            logger.error(f"Error unregistering agent {agent_name}: {e}")
            return False

    def list_registered_agents(self) -> List[AgentManifest]:
        """Lista todos los agentes registrados"""
        return list(self._registered_agents.values())

    def get_agent_manifest(self, agent_name: str) -> Optional[AgentManifest]:
        """Obtiene el manifiesto de un agente específico"""
        return self._registered_agents.get(agent_name)

    def is_agent_registered(self, agent_name: str) -> bool:
        """Verifica si un agente está registrado"""
        return agent_name in self._registered_agents

    def refresh_registry(self) -> int:
        """Recarga el registro desde el almacenamiento"""
        old_count = len(self._registered_agents)
        self._load_existing_agents()
        new_count = len(self._registered_agents)

        logger.info(f"Registry refreshed: {old_count} -> {new_count} agents")
        return new_count

    def get_registry_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del registro de agentes"""
        manifests = list(self._registered_agents.values())

        categories = {}
        for manifest in manifests:
            category = manifest.category
            categories[category] = categories.get(category, 0) + 1

        enabled_agents = len([
            name for name in self._registered_agents.keys()
            if self.config_service.is_enabled(name)
        ])
        recent_cutoff = datetime.now() - timedelta(days=7)
        recent_registrations = 0
        for manifest in manifests:
            created_raw = manifest.created_at or manifest.metadata.get("registered_at")
            if not created_raw:
                continue
            normalized = str(created_raw).replace('Z', '+00:00')
            parsed_dt = None
            candidates = [normalized]
            if '.' in normalized:
                candidates.append(normalized.split('.')[0])
            for candidate in candidates:
                if not candidate:
                    continue
                try:
                    parsed_dt = datetime.fromisoformat(candidate)
                    break
                except ValueError:
                    continue
            if parsed_dt and parsed_dt >= recent_cutoff:
                recent_registrations += 1

        return {
            "total_agents": len(manifests),
            "categories": categories,
            "enabled_agents": enabled_agents,
            "recent_registrations": recent_registrations,
        }