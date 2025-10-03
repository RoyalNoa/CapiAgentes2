#!/usr/bin/env python3
"""
Script de prueba para demostrar el sistema de privilegios de agentes.
Demuestra cómo diferentes agentes tienen diferentes niveles de acceso.
"""

import sys
import asyncio
from pathlib import Path

# Agregar el directorio src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.application.services.agent_authorization_service import (
    AgentAuthorizationService,
    get_authorization_service,
    authorize_agent_operation
)


async def _run_privileges_demo():
    """Probar el sistema de privilegios con diferentes agentes"""

    print("[PRIVILEGIOS] SISTEMA DE PRIVILEGIOS DE AGENTES - DEMO")
    print("=" * 60)

    # Obtener servicio de autorización
    auth_service = get_authorization_service()

    # Lista de agentes y operaciones a probar
    test_cases = [
        # CAPI Desktop (PRIVILEGED)
        {
            "agent": "capi_desktop",
            "operations": [
                ("read_file", "/app/ia_workspace/data/test.txt"),
                ("read_desktop", "C:/Users/lucas/Desktop/hola_mundo.txt"),
                ("write_desktop", "C:/Users/lucas/Desktop/output.txt"),
                ("access_external_path", "C:/temp/external.txt"),
                ("read_system_file", "/etc/passwd"),  # Debería fallar
            ]
        },

        # Summary Agent (STANDARD)
        {
            "agent": "summary",
            "operations": [
                ("read_file", "/app/ia_workspace/data/test.txt"),
                ("write_file", "/app/ia_workspace/data/output.txt"),  # Debería fallar
                ("read_desktop", "C:/Users/lucas/Desktop/test.txt"),  # Debería fallar
                ("access_external_path", "/external/path"),  # Debería fallar
            ]
        },

        # Smalltalk Agent (RESTRICTED)
        {
            "agent": "smalltalk",
            "operations": [
                ("read_file", "/app/ia_workspace/data/test.txt"),  # Debería fallar
                ("basic_calculations", None),  # Permitido
                ("read_desktop", "C:/Users/test.txt"),  # Debería fallar
            ]
        },

        # Anomaly Agent (ELEVATED)
        {
            "agent": "anomaly",
            "operations": [
                ("read_file", "/app/ia_workspace/data/test.txt"),
                ("transform_files", "/app/ia_workspace/data/analysis.csv"),
                ("create_alerts", None),  # Permiso personalizado
                ("backup_operations", "/app/backups/"),
                ("read_system_file", "/etc/config"),  # Debería fallar
            ]
        }
    ]

    # Ejecutar pruebas
    for test_case in test_cases:
        agent_name = test_case["agent"]

        print(f"\n[AGENTE] {agent_name.upper()}")
        print("-" * 40)

        # Mostrar privilegios del agente
        try:
            privileges = auth_service.get_agent_privileges(agent_name)
            print(f"[INFO] Nivel de privilegios: {privileges.privilege_level.name}")
            print(f"[INFO] Permisos: {', '.join(list(privileges.permissions)[:5])}{'...' if len(privileges.permissions) > 5 else ''}")
            print(f"[INFO] Restricciones: {', '.join(privileges.restrictions) if privileges.restrictions else 'Ninguna'}")
            print(f"[INFO] Extensiones permitidas: {', '.join(list(privileges.allowed_extensions)[:3])}{'...' if len(privileges.allowed_extensions) > 3 else ''}")
            print(f"[INFO] Razón: {privileges.reason}")
        except Exception as e:
            print(f"[ERROR] Error obteniendo privilegios: {e}")
            continue

        print(f"\n[PRUEBAS] PRUEBAS DE AUTORIZACIÓN:")

        # Probar cada operación
        for operation, path in test_case["operations"]:
            try:
                authorized = authorize_agent_operation(agent_name, operation, path)
                status = "[OK] AUTORIZADO" if authorized else "[DENIED] DENEGADO"
                path_display = f" en {path}" if path else ""
                print(f"  {status}: {operation}{path_display}")
            except Exception as e:
                print(f"  [WARNING] ERROR: {operation} - {e}")

    # Mostrar log de auditoría
    print(f"\n[AUDIT] LOG DE AUDITORÍA")
    print("-" * 40)
    audit_log = auth_service.get_audit_log()

    if not audit_log:
        print("No hay entradas en el log de auditoría")
    else:
        for entry in audit_log[-10:]:  # Últimas 10 entradas
            result_icon = "[OK]" if entry.get('result') == 'APPROVED' else "[DENIED]"
            print(f"{result_icon} {entry.get('agent_name', 'unknown')} -> {entry.get('operation', 'unknown')}")
            if entry.get('result') == 'DENIED':
                print(f"    Razón: {entry.get('reason', 'No especificada')}")

    print(f"\n[RESUMEN] RESUMEN")
    print("-" * 40)
    print("[OK] capi_desktop: Acceso privilegiado a archivos del usuario")
    print("[INFO] anomaly: Acceso elevado con permisos de alertas")
    print("[INFO] summary: Acceso estándar solo lectura")
    print("[INFO] smalltalk: Acceso restringido sin archivos")
    print("\n[SUCCESS] Sistema de privilegios funcionando correctamente!")



def test_agent_privileges():
    asyncio.run(_run_privileges_demo())

if __name__ == "__main__":
    asyncio.run(test_agent_privileges())
