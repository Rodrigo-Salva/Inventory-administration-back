"""Que el proyecto arranque igual en cualquier maquina (Windows incluido) tras clonar."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_env_example_is_plain_ascii():
    """Un .env copiado de la plantilla no debe depender de la codificacion del sistema."""
    text = (ROOT / ".env.example").read_bytes()
    assert all(b < 128 for b in text), "El .env.example solo debe contener caracteres ASCII"


def test_app_imports_even_if_dotenv_has_non_ascii_characters(tmp_path):
    """Regresion: slowapi leia .env con cp1252 y la app no arrancaba si tenia tildes."""
    (tmp_path / ".env").write_bytes(
        "DATABASE_URL=postgresql+asyncpg://u:p@localhost:5432/x\nSECRET_KEY=abc\nSMTP_FROM=Soporte Pérez ñ\n".encode("utf-8")
    )
    result = subprocess.run(
        [sys.executable, "-W", "ignore", "-c", "import app.infrastructure.security.rate_limit"],
        cwd=tmp_path, capture_output=True, text=True,
        env={"PYTHONPATH": str(ROOT), "PATH": "", "SYSTEMROOT": __import__("os").environ.get("SYSTEMROOT", "")},
    )
    assert result.returncode == 0, result.stderr[-800:]
