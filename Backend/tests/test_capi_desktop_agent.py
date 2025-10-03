from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = BACKEND_ROOT / "src"
IA_WORKSPACE_PATH = BACKEND_ROOT / "ia_workspace"

for candidate in (SRC_PATH, IA_WORKSPACE_PATH):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from agentes.capi_desktop.handler import CapiDesktop
from src.domain.agents.agent_protocol import BaseAgent


@pytest.mark.asyncio
async def test_read_excel_creates_txt_copy(tmp_path: Path):
    """Verifica que la lectura de Excel genere una copia en texto y la archive."""
    df = pd.DataFrame({"columna": [1, 2, 3]})
    source_path = tmp_path / "hola mundo.xlsx"
    df.to_excel(source_path, index=False)

    agent = CapiDesktop.__new__(CapiDesktop)
    BaseAgent.__init__(agent, "capi_desktop")

    agent.desktop_path = tmp_path
    agent.backup_path = tmp_path / "backups"
    agent.backup_path.mkdir(parents=True, exist_ok=True)
    agent.workspace_root = tmp_path
    agent.data_root = tmp_path
    agent.output_root = tmp_path / "agent-output"
    agent.output_root.mkdir(parents=True, exist_ok=True)
    agent.allowed_extensions = {'.csv', '.xlsx', '.xls', '.docx', '.doc', '.txt', ''}
    agent.max_file_size_mb = 50

    params = {
        'filename': 'hola mundo',
        'create_txt_copy': True,
        'txt_filename': 'hola_mundo_resumen'
    }

    result = await agent._read_excel_file(params)

    assert result.success is True
    generated = result.data.get('generated_txt')
    assert generated, "Se debe generar información del archivo de texto"

    txt_path = Path(generated['path'])
    assert txt_path.exists(), "El archivo de texto no fue creado"
    content = txt_path.read_text(encoding='utf-8')
    assert 'hola mundo.xlsx' in content

    archive_path = generated.get('archived_copy')
    assert archive_path is not None
    assert Path(archive_path).exists(), "No se creó la copia en agent-output"

