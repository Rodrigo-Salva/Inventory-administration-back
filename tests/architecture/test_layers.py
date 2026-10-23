"""Hace cumplir la regla de dependencias de Clean Architecture.

    presentation -> application -> domain      (infrastructure implementa los puertos)

* domain: solo biblioteca estándar y otros módulos de domain.
* application: puede usar domain y application; nunca infrastructure ni presentation.
* infrastructure: puede usar domain y application; nunca presentation.
* Fuera de presentation no se importa FastAPI.
"""

import ast
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[2] / "app"

FORBIDDEN = {
    "domain": ("app.application", "app.infrastructure", "app.presentation", "fastapi", "sqlalchemy", "pydantic"),
    "application": ("app.infrastructure", "app.presentation", "fastapi"),
    "infrastructure": ("app.presentation",),
}
# Excepciones documentadas y temporales (deuda explícita). Debe tender a vacío.
KNOWN_DEBT: dict[str, set[str]] = {}


def _imports(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            yield node.lineno, node.module
        elif isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name


def _violations(layer: str):
    found = []
    for path in sorted((APP / layer).rglob("*.py")):
        relative = path.relative_to(APP.parent).as_posix()
        for line, module in _imports(path):
            if any(module == f or module.startswith(f + ".") for f in FORBIDDEN[layer]):
                found.append(f"{relative}:{line} importa {module}")
    return found


@pytest.mark.parametrize("layer", ["domain", "application", "infrastructure"])
def test_dependency_rule(layer):
    allowed = KNOWN_DEBT.get(layer, set())
    violations = [v for v in _violations(layer) if not any(a in v for a in allowed)]
    assert not violations, f"Violaciones en {layer}:\n" + "\n".join(violations)


def test_app_root_only_contains_the_four_layers():
    entries = {p.name for p in APP.iterdir() if p.name != "__pycache__"}
    assert entries == {"domain", "application", "infrastructure", "presentation", "main.py", "__init__.py"}
