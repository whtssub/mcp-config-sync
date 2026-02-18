"""Tests for config: init, load, save, add_server, remove_server."""

import json
from pathlib import Path

import pytest

from mcp_sync.config import (
    add_server_to_master,
    ensure_master_config_dir,
    init_master_config,
    load_master_config,
    remove_server_from_master,
    save_master_config,
)
from mcp_sync.models import MasterConfig, MCPServerEntry


def test_init_creates_dir_and_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MCP_CONFIG_SYNC_CONFIG_DIR", str(tmp_path))
    path = init_master_config()
    assert path == tmp_path / "master.json"
    assert path.exists()
    data = json.loads(path.read_text())
    assert "mcpServers" in data
    assert data["mcpServers"] == {}


def test_load_master_config_empty_when_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MCP_CONFIG_SYNC_CONFIG_DIR", str(tmp_path))
    config = load_master_config()
    assert config.mcpServers == {}


def test_add_and_remove_server(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MCP_CONFIG_SYNC_CONFIG_DIR", str(tmp_path))
    init_master_config()
    add_server_to_master("x", command="npx", args=["-y", "pkg"], env=None, keyring_env_keys=["TOKEN"])
    config = load_master_config()
    assert "x" in config.mcpServers
    assert config.mcpServers["x"].command == "npx"
    assert config.mcpServers["x"].env_keys_from_keyring == ["TOKEN"]
    entry = remove_server_from_master("x")
    assert entry is not None
    assert load_master_config().mcpServers == {}
    entry2 = remove_server_from_master("x")
    assert entry2 is None


def test_load_master_config_invalid_json_returns_empty(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MCP_CONFIG_SYNC_CONFIG_DIR", str(tmp_path))
    (tmp_path / "master.json").write_text("not valid json {")
    config = load_master_config()
    assert config.mcpServers == {}


def test_add_overwrite_cleans_old_keyring_keys(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When re-adding a server with fewer --key args, old keyring keys should be removed from keyring."""
    from unittest.mock import MagicMock

    monkeypatch.setenv("MCP_CONFIG_SYNC_CONFIG_DIR", str(tmp_path))
    init_master_config()
    add_server_to_master("srv", command="npx", args=[], env=None, keyring_env_keys=["OLD_KEY"])
    # Overwrite with only NEW_KEY (no OLD_KEY) - should call delete_all_keys_for_server(srv, ["OLD_KEY"])
    with monkeypatch.context() as m:
        delete_mock = MagicMock()
        m.setattr("mcp_sync.config.delete_all_keys_for_server", delete_mock)
        add_server_to_master("srv", command="npx", args=["-y", "pkg"], env=None, keyring_env_keys=["NEW_KEY"])
        delete_mock.assert_called_once_with("srv", ["OLD_KEY"])
