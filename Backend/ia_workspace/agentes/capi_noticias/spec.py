"""
Especificacion del agente Capi Noticias
Autor: Codex Autogen
Ultima actualizacion: 2025-09-18
"""

AGENT_NAME = "capi_noticias"
VERSION = "1.0.0"
DISPLAY_NAME = "Capi Noticias"

SUPPORTED_INTENTS = [
    "news_monitoring",
    "news_report"
]

CAPABILITIES = {
    "financial_news": True,
    "cash_flow_risk": True,
    "multi_source": True,
    "auto_schedule": True,
    "manual_refresh": True
}

METADATA = {
    "description": "Analista financiero que monitorea noticias de Ambito.com para anticipar impactos en el flujo de efectivo de sucursales.",
    "category": "market_intelligence",
    "tags": ["news", "liquidity", "cash", "branches", "risk"],
    "author": "Codex Autogen",
    "data_sources": ["https://www.ambito.com"],
    "output_formats": ["json", "text"],
    "documentation": "docs/CatalogoAgentes.md#capi-noticias"
}
