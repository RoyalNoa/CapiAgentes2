"""Punto de entrada del Capi Desktop."""

from .handler import CapiDesktop
from .spec import (
    AGENT_NAME,
    VERSION,
    DISPLAY_NAME,
    SUPPORTED_INTENTS,
    CAPABILITIES,
    METADATA,
)

__all__ = [
    'CapiDesktop',
    'AGENT_NAME',
    'VERSION',
    'DISPLAY_NAME',
    'SUPPORTED_INTENTS',
    'CAPABILITIES',
    'METADATA',
]