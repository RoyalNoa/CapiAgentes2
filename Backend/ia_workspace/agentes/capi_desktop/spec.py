"""
Especificación del Capi Desktop
Autor: Claude Code
Última actualización: 2025-09-14
"""

# Metadatos del agente según ARCHITECTURE.md
AGENT_NAME = "capi_desktop"
VERSION = "1.0.0"
DISPLAY_NAME = "Capi Desktop"

# Intents soportados
SUPPORTED_INTENTS = [
    "documentar_analisis",
    "generar_reporte",
    "escribir_documento",
    "documentar_procesos"
]

# Capacidades del agente
CAPABILITIES = {
    "document_generation": True,
    "financial_documentation": True,
    "process_documentation": True,
    "report_generation": True,
    "multilingual": True,
    "template_support": True
}

# Metadatos adicionales
METADATA = {
    "description": "Agente especializado en documentación y generación de reportes financieros",
    "category": "documentation",
    "author": "Claude Code",
    "tags": ["documentation", "reporting", "financial", "analysis"],
    "dependencies": ["pandas", "pathlib", "datetime"],
    "data_sources": ["financial_records", "analysis_results"],
    "output_formats": ["markdown", "json", "text"]
}