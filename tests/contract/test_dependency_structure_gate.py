"""Structural dependency gate using AST imports (stronger than textual search)."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]


def _iter_imports(py_file: Path) -> Iterable[str]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                yield node.module


def test_operational_files_do_not_depend_on_research_or_legacy_runtime():
    operational_files = [
        REPO_ROOT / "src" / "api" / "server.py",
        REPO_ROOT / "src" / "analysis" / "manager_ai.py",
        REPO_ROOT / "src" / "training" / "trainer.py",
        REPO_ROOT / "src" / "ml" / "train_neural.py",
        REPO_ROOT / "scripts" / "train_model.py",
    ]

    forbidden_prefixes = [
        "research",
        "src.web.server",
        "src.web.scanner_manager",
    ]

    for py_file in operational_files:
        imports = list(_iter_imports(py_file))
        for imp in imports:
            for forbidden in forbidden_prefixes:
                assert not imp.startswith(forbidden), f"{py_file} imports forbidden dependency: {imp}"
