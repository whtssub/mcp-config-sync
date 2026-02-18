"""Tests for path resolution and get_detected_clients."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_sync.paths import (
    get_detected_clients,
    get_master_config_dir,
    get_master_config_path,
    get_platform_client_paths,
)


def test_get_master_config_dir_uses_platformdirs() -> None:
    d = get_master_config_dir()
    assert "mcp-config-sync" in str(d)
    assert d == get_master_config_path().parent


def test_master_config_dir_override_via_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_CONFIG_SYNC_CONFIG_DIR", "/tmp/mcp-test")
    d = get_master_config_dir()
    assert d.resolve() == Path("/tmp/mcp-test").resolve()
    assert get_master_config_path().name == "master.json"
    assert get_master_config_path().parent == d


def test_get_platform_client_paths_returns_all_clients() -> None:
    paths = get_platform_client_paths()
    assert "claude_desktop" in paths
    assert "cursor" in paths
    assert "windsurf" in paths
    assert "vscode" in paths
    for p in paths.values():
        assert isinstance(p, Path)
        assert "mcp" in str(p).lower() or "claude" in str(p).lower() or "codeium" in str(p)


def test_get_detected_clients_only_existing(tmp_path: Path) -> None:
    """When paths are under tmp_path and only some exist, only those are returned."""
    (tmp_path / "a.json").write_text("{}")
    (tmp_path / "b.json").write_text("{}")
    with patch("mcp_sync.paths.get_platform_client_paths") as m:
        m.return_value = {
            "client_a": tmp_path / "a.json",
            "client_b": tmp_path / "b.json",
            "client_missing": tmp_path / "missing.json",
        }
        detected = get_detected_clients()
    names = [c[0] for c in detected]
    assert "client_a" in names
    assert "client_b" in names
    assert "client_missing" not in names
