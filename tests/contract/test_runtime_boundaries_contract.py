"""Contracts for runtime boundaries between operational and research/legacy modules."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_research_and_legacy_modules_are_classified_explicitly():
    """Modules outside production runtime must declare explicit destination classification."""
    research_files = [
        "research/analysis/drift_check.py",
        "research/analysis/stationarity.py",
        "research/scripts/backtest_model.py",
        "research/scripts/backtest_system.py",
        "research/scripts/audit_stationarity.py",
        "research/scripts/audit_calibration_ece.py",
        "research/scripts/cleanup_zombies.py",
        "research/scripts/force_clear_pending.py",
        "research/scripts/list_pending.py",
        "research/scripts/scientific_validation.py",
        "research/scripts/validate_health.py",
        "research/scripts/verify_reproducibility.py",
    ]
    legacy_files = [
        "src/web/server.py",
        "src/web/scanner_manager.py",
    ]

    for file_path in research_files:
        assert "CLASSIFICATION: MOVE TO RESEARCH" in _read(file_path), file_path

    for file_path in legacy_files:
        assert "CLASSIFICATION: MOVE TO LEGACY" in _read(file_path), file_path


def test_operational_runtime_does_not_import_research_or_legacy_modules():
    """Operational entrypoints must stay decoupled from research and legacy runtime paths."""
    operational_files = [
        "src/api/server.py",
        "src/analysis/manager_ai.py",
        "src/training/trainer.py",
        "scripts/train_model.py",
        "src/ml/train_neural.py",
        "src/scripts/save_production_calibrator.py",
    ]

    forbidden_tokens = [
        "research.analysis.drift_check",
        "research.analysis.stationarity",
        "research.scripts.backtest_model",
        "research.scripts.audit_stationarity",
        "research.scripts.audit_calibration_ece",
        "src.web.server",
        "src.web.scanner_manager",
    ]

    for file_path in operational_files:
        content = _read(file_path)
        for token in forbidden_tokens:
            assert token not in content, f"{file_path} must not import {token}"


def test_experimental_modules_were_physically_moved_out_of_src():
    """Experimental modules must no longer exist under src/ after Phase 6 move."""
    moved_from_src = [
        "src/analysis/drift_check.py",
        "src/analysis/stationarity.py",
        "src/scripts/backtest_model.py",
        "src/scripts/backtest_system.py",
        "src/scripts/audit_stationarity.py",
        "src/scripts/audit_calibration_ece.py",
        "src/scripts/cleanup_zombies.py",
        "src/scripts/force_clear_pending.py",
        "src/scripts/list_pending.py",
        "src/scripts/scientific_validation.py",
        "src/scripts/validate_health.py",
        "src/scripts/verify_reproducibility.py",
    ]

    for file_path in moved_from_src:
        assert not (REPO_ROOT / file_path).exists(), file_path


def test_src_scripts_contains_only_operational_calibrator_entrypoint():
    """src/scripts should not accumulate orphan scripts after research extraction."""
    expected_operational_scripts = {
        "save_production_calibrator.py",
    }
    scripts_dir = REPO_ROOT / "src" / "scripts"
    current_scripts = {p.name for p in scripts_dir.glob("*.py")}
    assert current_scripts == expected_operational_scripts, current_scripts
