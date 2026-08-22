import pytest


@pytest.fixture()
def isolated_env(tmp_path, monkeypatch):
    """config/dataディレクトリを一時ディレクトリに向け、実データを汚さないようにする。"""
    config_dir = tmp_path / "config"
    data_dir = tmp_path / "data"
    config_dir.mkdir()
    data_dir.mkdir()
    monkeypatch.setenv("AUTOX_CONFIG_DIR", str(config_dir))
    monkeypatch.setenv("AUTOX_DATA_DIR", str(data_dir))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    return {"config_dir": config_dir, "data_dir": data_dir}
