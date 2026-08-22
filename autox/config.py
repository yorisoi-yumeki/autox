"""設定ファイル・データディレクトリの場所解決とYAML読み込み。

パスは関数として都度解決する(モジュールimport時に固定しない)。
これによりテストコードが AUTOX_CONFIG_DIR / AUTOX_DATA_DIR を
monkeypatchするだけで、一時ディレクトリに向けて動作を検証できる。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

_PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = _PACKAGE_DIR.parent


def config_dir() -> Path:
    return Path(os.environ.get("AUTOX_CONFIG_DIR", PROJECT_ROOT / "config"))


def data_dir() -> Path:
    return Path(os.environ.get("AUTOX_DATA_DIR", PROJECT_ROOT / "data"))


def settings_path() -> Path:
    return config_dir() / "settings.yaml"


def settings_example_path() -> Path:
    return config_dir() / "settings.example.yaml"


def profile_path() -> Path:
    return config_dir() / "profile.yaml"


def db_path() -> Path:
    return data_dir() / "autox.db"


def prompts_dir() -> Path:
    return data_dir() / "prompts"


def reports_dir() -> Path:
    return data_dir() / "reports"


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def load_settings() -> dict[str, Any]:
    """config/settings.yaml を読み込む。無ければ example にフォールバック。"""
    path = settings_path()
    if path.exists():
        return _load_yaml(path)
    return _load_yaml(settings_example_path())


def load_profile() -> dict[str, Any]:
    """config/profile.yaml (価値観インタビューの回答)を読み込む。未作成なら空dict。"""
    return _load_yaml(profile_path())


def save_profile(profile: dict[str, Any]) -> Path:
    """profile.yaml に保存する。ディレクトリが無ければ作成する。"""
    config_dir().mkdir(parents=True, exist_ok=True)
    path = profile_path()
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(profile, f, allow_unicode=True, sort_keys=False)
    return path


def ensure_data_dirs() -> None:
    data_dir().mkdir(parents=True, exist_ok=True)
    prompts_dir().mkdir(parents=True, exist_ok=True)
    reports_dir().mkdir(parents=True, exist_ok=True)
