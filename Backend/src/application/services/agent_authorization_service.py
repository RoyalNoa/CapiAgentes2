"""
Servicio de autorización de agentes para control de acceso granular.
Implementa un sistema de privilegios basado en roles para agentes del sistema.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass
from enum import Enum

from src.core.exceptions import AuthorizationError, ValidationError

logger = logging.getLogger(__name__)


class PrivilegeLevel(Enum):
    """Niveles de privilegios disponibles"""
    RESTRICTED = 1
    STANDARD = 2
    ELEVATED = 3
    PRIVILEGED = 4
    ADMIN = 5


@dataclass
class AgentPrivileges:
    """Configuración de privilegios de un agente"""
    agent_name: str
    privilege_level: PrivilegeLevel
    permissions: Set[str]
    custom_permissions: Set[str]
    restrictions: Set[str]
    allowed_extensions: Set[str]
    reason: str


class AgentAuthorizationService:
    """
    Servicio de autorización para agentes del sistema.

    Características:
    - Control de acceso basado en roles (RBAC)
    - Permisos granulares por agente
    - Restricciones de paths y extensiones
    - Auditoría completa de operaciones
    - Políticas de seguridad configurables
    """

    def __init__(self, config_path: Optional[Path] = None):
        """Inicializar servicio de autorización"""
        if config_path is None:
            # Usar path por defecto del workspace
            base_path = Path(__file__).parents[3] / "ia_workspace" / "data"
            config_path = base_path / "agent_privileges.json"

        self.config_path = config_path
        self.config = self._load_config()
        self.audit_log: List[Dict[str, Any]] = []
        # Connection info will be read from env DATABASE_URL when needed

        logger.info(f"AgentAuthorizationService initialized with config: {config_path}")

    def _load_config(self) -> Dict[str, Any]:
        """Cargar configuración de privilegios"""
        try:
            if not self.config_path.exists():
                raise FileNotFoundError(f"Archivo de privilegios no encontrado: {self.config_path}")

            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # Validar estructura básica
            required_keys = ['privilege_levels', 'agent_assignments', 'security_policies']
            for key in required_keys:
                if key not in config:
                    raise ValidationError(f"Clave requerida '{key}' no encontrada en configuración")

            logger.info("Configuración de privilegios cargada exitosamente")
            return config

        except Exception as e:
            logger.error(f"Error cargando configuración de privilegios: {e}")
            raise AuthorizationError(f"No se pudo cargar configuración de privilegios: {e}")

    def _get_db_privilege_level(self, agent_name: str) -> Optional[str]:
        """Intenta obtener nivel_privilegio desde la BD (public.agentes) de forma síncrona.

        Usa psycopg2 y la variable de entorno DATABASE_URL. Si no está disponible
        o hay error, devuelve None y el sistema seguirá con la configuración JSON.
        """
        dsn = os.getenv('DATABASE_URL')
        if not dsn:
            return None
        try:
            # Importación perezosa para no requerir psycopg2 en entornos sin Postgres
            import psycopg2  # type: ignore
            # Conexión rápida con timeout corto
            conn = psycopg2.connect(dsn, connect_timeout=2)
            try:
                with conn, conn.cursor() as cur:
                    cur.execute(
                        "SELECT nivel_privilegio FROM public.agentes WHERE nombre = %s LIMIT 1",
                        (agent_name,),
                    )
                    row = cur.fetchone()
                    if row and row[0]:
                        return row[0]
            finally:
                conn.close()
        except Exception as e:
            logger.debug(f"No se pudo leer nivel_privilegio de BD para {agent_name}: {e}")
        return None

    def get_agent_privileges(self, agent_name: str) -> AgentPrivileges:
        """Obtener privilegios de un agente específico"""
        try:
            agent_config = self.config.get('agent_assignments', {}).get(agent_name)
            if not agent_config:
                # Usar configuración por defecto para agentes no registrados
                agent_config = {
                    'privilege_level': 'restricted',
                    'custom_permissions': [],
                    'restrictions': ['no_file_access', 'no_system_access'],
                    'reason': 'Agente no registrado - acceso mínimo'
                }

            # Obtener nivel de privilegios (prioridad: BD -> config JSON -> 'restricted')
            privilege_level_name = self._get_db_privilege_level(agent_name) or agent_config.get('privilege_level', 'restricted')
            # Validación segura del nivel
            try:
                privilege_level = PrivilegeLevel[privilege_level_name.upper()]
            except KeyError:
                logger.warning(
                    f"Nivel de privilegio desconocido '{privilege_level_name}' para {agent_name}, usando RESTRICTED"
                )
                privilege_level = PrivilegeLevel.RESTRICTED

            # Obtener permisos base del nivel
            level_config = self.config['privilege_levels'].get(privilege_level_name, {})
            base_permissions = set(level_config.get('permissions', []))

            # Si tiene permisos de admin (*), incluir todos los permisos
            if '*' in base_permissions:
                all_permissions = set()
                for level in self.config['privilege_levels'].values():
                    all_permissions.update(level.get('permissions', []))
                all_permissions.discard('*')  # Remover el wildcard
                base_permissions = all_permissions

            # Agregar permisos personalizados
            custom_permissions = set(agent_config.get('custom_permissions', []))
            all_permissions = base_permissions.union(custom_permissions)

            # Obtener restricciones
            restrictions = set(agent_config.get('restrictions', []))

            # Obtener extensiones permitidas
            allowed_extensions = set(
                self.config.get('allowed_extensions', {}).get(
                    agent_name,
                    self.config.get('allowed_extensions', {}).get('default', [])
                )
            )

            return AgentPrivileges(
                agent_name=agent_name,
                privilege_level=privilege_level,
                permissions=all_permissions,
                custom_permissions=custom_permissions,
                restrictions=restrictions,
                allowed_extensions=allowed_extensions,
                reason=agent_config.get('reason', 'Sin razón especificada')
            )

        except Exception as e:
            logger.error(f"Error obteniendo privilegios para agente {agent_name}: {e}")
            raise AuthorizationError(f"No se pudieron obtener privilegios para {agent_name}: {e}")

    def authorize_operation(self, agent_name: str, operation: str,
                          path: Optional[str] = None, **kwargs) -> bool:
        """
        Autorizar una operación específica para un agente.

        Args:
            agent_name: Nombre del agente
            operation: Operación a autorizar (ej: 'read_file', 'write_file', etc.)
            path: Path del archivo/directorio (opcional)
            **kwargs: Parámetros adicionales para la autorización

        Returns:
            bool: True si la operación está autorizada, False caso contrario

        Raises:
            AuthorizationError: Si hay un error en el proceso de autorización
        """
        try:
            privileges = self.get_agent_privileges(agent_name)

            # Registrar intento de autorización
            audit_entry = {
                'agent_name': agent_name,
                'operation': operation,
                'path': path,
                'timestamp': logger.name,  # Simplificado para este ejemplo
                'additional_params': kwargs
            }

            # Verificar si la operación está permitida por los permisos
            if not self._check_permission(privileges, operation):
                audit_entry['result'] = 'DENIED'
                audit_entry['reason'] = 'Permisos insuficientes'
                self._log_audit(audit_entry)
                return False

            # Verificar restricciones específicas
            if self._check_restrictions(privileges, operation, path):
                audit_entry['result'] = 'DENIED'
                audit_entry['reason'] = 'Operación restringida'
                self._log_audit(audit_entry)
                return False

            # Verificar path si se proporciona
            if path and not self._check_path_access(privileges, path, operation):
                audit_entry['result'] = 'DENIED'
                audit_entry['reason'] = 'Acceso a path denegado'
                self._log_audit(audit_entry)
                return False

            # Autorización exitosa
            audit_entry['result'] = 'APPROVED'
            self._log_audit(audit_entry)

            logger.info(f"Operación autorizada: {agent_name} -> {operation} en {path}")
            return True

        except Exception as e:
            logger.error(f"Error en autorización: {e}")
            raise AuthorizationError(f"Error en proceso de autorización: {e}")

    def _check_permission(self, privileges: AgentPrivileges, operation: str) -> bool:
        """Verificar si el agente tiene permisos para la operación"""
        # Mapeo de operaciones a permisos requeridos
        operation_permissions = {
            'read_file': 'read_workspace_data',
            'write_file': 'write_workspace_data',
            'read_system_file': 'read_system_files',
            'write_system_file': 'write_system_files',
            'transform_file': 'transform_files',
            'backup_file': 'backup_operations',
            'execute_command': 'execute_system_commands',
            'read_desktop': 'read_user_desktop',
            'write_desktop': 'write_user_desktop',
            'access_external_path': 'access_external_paths'
        }

        required_permission = operation_permissions.get(operation, operation)
        return required_permission in privileges.permissions

    def _check_restrictions(self, privileges: AgentPrivileges,
                          operation: str, path: Optional[str]) -> bool:
        """Verificar si hay restricciones que impidan la operación"""
        restrictions = privileges.restrictions

        # Restricciones comunes
        if 'no_file_access' in restrictions and operation.endswith('_file'):
            return True

        if 'no_system_access' in restrictions and 'system' in operation:
            return True

        if 'no_file_write' in restrictions and operation.startswith('write'):
            return True

        if path and 'no_system_critical_files' in restrictions:
            return self._is_critical_system_path(path)

        return False

    def _check_path_access(self, privileges: AgentPrivileges,
                         path: str, operation: str) -> bool:
        """Verificar acceso a un path específico"""
        path_obj = Path(path)

        # Verificar paths restringidos globalmente
        restricted_paths = self.config.get('restricted_paths', [])
        for restricted in restricted_paths:
            if restricted.endswith('*'):
                # Wildcard matching
                pattern = restricted[:-1]
                if str(path_obj).startswith(pattern):
                    return False
            elif str(path_obj).startswith(restricted):
                return False

        # Verificar extensiones permitidas
        if path_obj.suffix and path_obj.suffix not in privileges.allowed_extensions:
            return False

        return True

    def _is_critical_system_path(self, path: str) -> bool:
        """Verificar si un path es crítico del sistema"""
        critical_patterns = [
            '/etc/', '/root/', '/sys/', '/proc/',
            'C:\\Windows\\System32\\', 'C:\\Program Files\\',
            '.exe', '.dll', '.sys'
        ]

        return any(pattern in path for pattern in critical_patterns)

    def _log_audit(self, entry: Dict[str, Any]) -> None:
        """Registrar entrada de auditoría"""
        if self.config.get('security_policies', {}).get('audit_trail', True):
            self.audit_log.append(entry)

            # Log crítico para operaciones denegadas
            if entry.get('result') == 'DENIED':
                logger.warning(f"Acceso denegado: {entry}")

    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Obtener log de auditoría"""
        return self.audit_log.copy()

    def elevate_privileges(self, agent_name: str, target_level: str,
                         justification: str) -> bool:
        """
        Elevar privilegios de un agente (si está permitido por políticas).
        NOTA: Por defecto está deshabilitado por seguridad.
        """
        if not self.config.get('security_policies', {}).get('privilege_escalation_allowed', False):
            logger.warning(f"Intento de elevación de privilegios denegado para {agent_name}")
            return False

        # Implementar lógica de elevación temporal si fuera necesario
        logger.info(f"Elevación de privilegios para {agent_name} a {target_level}: {justification}")
        return True


# Instancia global del servicio (singleton)
_authorization_service: Optional[AgentAuthorizationService] = None


def get_authorization_service() -> AgentAuthorizationService:
    """Obtener instancia del servicio de autorización (singleton)"""
    global _authorization_service
    if _authorization_service is None:
        _authorization_service = AgentAuthorizationService()
    return _authorization_service


def authorize_agent_operation(agent_name: str, operation: str,
                            path: Optional[str] = None, **kwargs) -> bool:
    """Función de conveniencia para autorizar operaciones"""
    service = get_authorization_service()
    return service.authorize_operation(agent_name, operation, path, **kwargs)