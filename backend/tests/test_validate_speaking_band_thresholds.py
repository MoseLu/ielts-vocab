from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / 'scripts'
    / 'validate_speaking_band_thresholds.py'
)


def _load_script_module():
    spec = importlib.util.spec_from_file_location('validate_speaking_band_thresholds', SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_validate_speaking_band_thresholds_accepts_unset_config(tmp_path):
    module = _load_script_module()
    env_file = tmp_path / 'microservices.env'
    env_file.write_text('', encoding='utf-8')

    result = module.validate_speaking_band_thresholds(module.load_env_values(env_file))

    assert result.configured is False
    assert result.ready is True
    assert result.resolved_thresholds == []


def test_validate_speaking_band_thresholds_normalizes_valid_rows(tmp_path):
    module = _load_script_module()
    env_file = tmp_path / 'microservices.env'
    env_file.write_text(
        'SPEAKING_ASSESSMENT_BAND_THRESHOLDS_JSON=[[89,8.49],{"min_score":76,"band":7.6}]',
        encoding='utf-8',
    )

    result = module.validate_speaking_band_thresholds(module.load_env_values(env_file))

    assert result.configured is True
    assert result.ready is True
    assert result.resolved_thresholds == [(89, 8.5), (76, 7.5), (0, 0.0)]


def test_validate_speaking_band_thresholds_rejects_invalid_json(tmp_path):
    module = _load_script_module()
    env_file = tmp_path / 'microservices.env'
    env_file.write_text(
        'SPEAKING_ASSESSMENT_BAND_THRESHOLDS_JSON=not-json',
        encoding='utf-8',
    )

    result = module.validate_speaking_band_thresholds(module.load_env_values(env_file))

    assert result.configured is True
    assert result.ready is False
    assert result.error.startswith('invalid JSON:')


def test_validate_speaking_band_thresholds_rejects_invalid_rows(tmp_path):
    module = _load_script_module()
    env_file = tmp_path / 'microservices.env'
    env_file.write_text(
        'SPEAKING_ASSESSMENT_BAND_THRESHOLDS_JSON=[["bad",7.0]]',
        encoding='utf-8',
    )

    result = module.validate_speaking_band_thresholds(module.load_env_values(env_file))

    assert result.configured is True
    assert result.ready is False
    assert result.error == 'row 1 minScore/band must be numeric'
