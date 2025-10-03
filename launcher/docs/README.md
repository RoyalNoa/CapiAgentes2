# Capi Launcher

Aplicación de escritorio en Tkinter para administrar los contenedores de CapiAgentes con una interfaz moderna inspirada en el diseño del chat.

## Características principales

- Tablero oscuro con indicadores LED de estado (verde/amarillo/rojo)
- Tarjetas verticales con acciones compactas (toggle iniciar/detener, reinicio, build, logs, eliminar) con iconografía minimalista
- Barra de herramientas global para start/stop/restart masivos, más botón "Capi Agentes" que abre la interfaz web
- Panel de log persistente (25 % del ancho) con historial de operaciones y salida de Docker
- Popup de error liviano en la esquina superior derecha y atajos de teclado (R para refrescar, L para ver logs)

## Requisitos

- Python 3.10+ (recomendado usar el .venv del proyecto)
- PyInstaller instalado (pip install pyinstaller dentro del entorno)
- Docker Desktop o daemon equivalente en ejecución

## Generar el ejecutable

Ejecutá el script:

`at
launcher\scripts\Build Launcher.bat
`

El proceso:

1. Limpia artefactos previos
2. Ejecuta PyInstaller con launcher/pyinstaller/CapiAgentes_Docker_Manager.spec
3. Copia Capi Launcher.exe en la raíz del repositorio

## Formas de ejecutar la app

- **Producción**: Capi Launcher.exe
- **Desarrollo**: python launcher/src/launcher_app/app.py

## Controles de la interfaz

### Tarjetas de servicio
- LED de estado + etiqueta (EN LÍNEA / INICIANDO / DETENIDO / ERROR)
- Datos rápidos: puerto, uptime, reinicios
- Botones: Build (si aplica), Iniciar, Detener, Reiniciar, Logs, Abrir URL, Eliminar
- Tarjeta dedicada **Elastic Observability** para el stack Elastic (usa el mismo set de acciones y abre Kibana en http://localhost:5601)

### Barra global
- Start/Stop/Restart masivos
- Refresh manual y contador de servicios activos

### Panel de log (25 % derecha)
- Cronología con timestamp
- Salida textual de Docker y PyInstaller (uild, start, stop, logs)

## Solución de problemas

- **Docker no responde**: verificar docker info y reiniciar Docker Desktop
- **Build falla**: confirmar que PyInstaller está disponible y que la terminal tiene permisos
- **Permisos PowerShell**: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
- **Puertos ocupados**: liberar 5432/8000/3000 o actualizar docker-compose.yml

---
Maintainer: equipo CapiAgentes
