"""Contract tests for Phase 8: ManagerAI runtime wiring to ModelRegistry."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_manager_ai_imports_model_registry():
    """ManagerAI must explicitly import ModelRegistry for runtime role resolution."""
    content = (REPO_ROOT / "src" / "analysis" / "manager_ai.py").read_text(encoding="utf-8")
    assert "from src.models.model_registry import ModelRegistry" in content


def test_manager_ai_defines_runtime_role_fields():
    """ManagerAI must keep explicit runtime champion/challenger role fields."""
    content = (REPO_ROOT / "src" / "analysis" / "manager_ai.py").read_text(encoding="utf-8")
    assert "self.runtime_champion_id" in content
    assert "self.runtime_challenger_id" in content
    assert "_resolve_runtime_model_roles" in content


def test_manager_ai_uses_registry_roles_in_line_selection():
    """Line selection must be driven by champion/challenger runtime roles."""
    content = (REPO_ROOT / "src" / "analysis" / "manager_ai.py").read_text(encoding="utf-8")
    assert "champion_raw" in content
    assert "challenger_raw" in content
    assert "projected_mu=champion_raw" in content
    assert "neural_mu=challenger_raw" in content
