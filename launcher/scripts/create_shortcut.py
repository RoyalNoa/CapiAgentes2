#!/usr/bin/env python3
"""
Script para crear un acceso directo al script Python
Como alternativa al ejecutable que tiene problemas
"""

import os
import sys
import subprocess
from pathlib import Path

def create_batch_launcher():
    """Crear un archivo .bat que lance la aplicación Python"""

    # Obtener la ruta actual
    current_dir = os.getcwd()
    python_script = os.path.join(current_dir, "capi_docker_manager.py")

    # Contenido del archivo batch
    batch_content = f"""@echo off
cd /d "{current_dir}"
echo Iniciando CapiAgentes Docker Manager...
echo.
python "{python_script}"
pause
"""

    # Crear el archivo .bat
    batch_file = "CapiAgentes_Docker_Manager.bat"

    try:
        with open(batch_file, 'w', encoding='utf-8') as f:
            f.write(batch_content)

        print(f"Archivo batch creado: {batch_file}")
        print(f"Ubicacion: {os.path.abspath(batch_file)}")
        print("\nInstrucciones:")
        print("1. Haz doble clic en el archivo .bat para ejecutar la aplicacion")
        print("2. Asegurate de tener Python instalado y Docker en funcionamiento")
        print("3. Puedes mover este archivo .bat a cualquier ubicacion")
        print("4. Para crear un acceso directo, haz clic derecho > Crear acceso directo")

        return True

    except Exception as e:
        print(f"Error al crear archivo batch: {e}")
        return False

def create_powershell_launcher():
    """Crear un archivo .ps1 que lance la aplicación Python"""

    # Obtener la ruta actual
    current_dir = os.getcwd()
    python_script = os.path.join(current_dir, "capi_docker_manager.py")

    # Contenido del archivo PowerShell
    ps_content = f"""# CapiAgentes Docker Manager Launcher
Write-Host "Iniciando CapiAgentes Docker Manager..." -ForegroundColor Green
Write-Host ""

# Cambiar al directorio del proyecto
Set-Location "{current_dir}"

# Verificar que Python este disponible
try {{
    $pythonVersion = python --version 2>&1
    Write-Host "Python detectado: $pythonVersion" -ForegroundColor Yellow
}} catch {{
    Write-Host "Error: Python no esta instalado o no esta en PATH" -ForegroundColor Red
    Write-Host "Instala Python desde https://python.org" -ForegroundColor Red
    Read-Host "Presiona Enter para salir"
    exit 1
}}

# Verificar que Docker este disponible
try {{
    $dockerVersion = docker --version 2>&1
    Write-Host "Docker detectado: $dockerVersion" -ForegroundColor Yellow
}} catch {{
    Write-Host "Advertencia: Docker no esta disponible" -ForegroundColor Yellow
    Write-Host "Asegurate de que Docker Desktop este ejecutandose" -ForegroundColor Yellow
}}

Write-Host ""
Write-Host "Lanzando aplicacion..." -ForegroundColor Green

# Ejecutar la aplicacion Python
python "{python_script}"

Write-Host ""
Write-Host "Aplicacion cerrada." -ForegroundColor Yellow
Read-Host "Presiona Enter para salir"
"""

    # Crear el archivo .ps1
    ps_file = "CapiAgentes_Docker_Manager.ps1"

    try:
        with open(ps_file, 'w', encoding='utf-8') as f:
            f.write(ps_content)

        print(f"Archivo PowerShell creado: {ps_file}")
        print(f"Ubicacion: {os.path.abspath(ps_file)}")
        print("\nPara ejecutar con PowerShell:")
        print("1. Haz clic derecho en el archivo .ps1")
        print("2. Selecciona 'Ejecutar con PowerShell'")
        print("3. Si aparece un error de politica, ejecuta:")
        print("   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser")

        return True

    except Exception as e:
        print(f"Error al crear archivo PowerShell: {e}")
        return False

def main():
    """Función principal"""
    print("CapiAgentes Docker Manager - Creador de Accesos Directos")
    print("=" * 65)

    # Verificar que el script principal existe
    if not os.path.exists("capi_docker_manager.py"):
        print("Error: No se encontro capi_docker_manager.py en el directorio actual")
        print("Asegurate de ejecutar este script desde el directorio correcto")
        return False

    print("Creando launchers alternativos al ejecutable...")
    print()

    # Crear archivo batch
    print("1. Creando launcher batch (.bat)...")
    batch_success = create_batch_launcher()
    print()

    # Crear archivo PowerShell
    print("2. Creando launcher PowerShell (.ps1)...")
    ps_success = create_powershell_launcher()
    print()

    if batch_success or ps_success:
        print("=" * 65)
        print("Launchers creados exitosamente!")
        print()
        print("Opciones para ejecutar la aplicacion:")

        if batch_success:
            print("- Doble clic en: CapiAgentes_Docker_Manager.bat")

        if ps_success:
            print("- Clic derecho > Ejecutar con PowerShell en: CapiAgentes_Docker_Manager.ps1")

        print("- Comando directo: python capi_docker_manager.py")
        print()
        print("Todos los launchers requieren:")
        print("- Python 3.7+ instalado")
        print("- Docker y Docker Compose disponibles")
        print("- Ejecutar desde el directorio del proyecto CapiAgentes")

        return True
    else:
        print("=" * 65)
        print("Hubo problemas al crear los launchers.")
        print("Puedes ejecutar directamente: python capi_docker_manager.py")
        return False

if __name__ == "__main__":
    success = main()
    input("\nPresiona Enter para salir...")
    sys.exit(0 if success else 1)