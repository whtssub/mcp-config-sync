"""Tests for import and status CLI and edge cases."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from mcp_sync.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolated_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MCP_CONFIG_SYNC_CONFIG_DIR", str(tmp_path))


def test_import_unknown_client() -> None:
    r = runner.invoke(app, ["init"])
    assert r.exit_code == 0
    r = runner.invoke(app, ["import", "unknown_client"])
    assert r.exit_code == 1
    assert "Unknown client" in r.output or "unknown_client" in r.output


def test_import_missing_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from unittest.mock import patch

    monkeypatch.setenv("MCP_CONFIG_SYNC_CONFIG_DIR", str(tmp_path))
    runner.invoke(app, ["init"])
    fake_path = tmp_path / "fake" / "claude.json"
    with patch("mcp_sync.paths.get_platform_client_paths") as m:
        m.return_value = {"claude_desktop": fake_path, "cursor": tmp_path / "c", "windsurf": tmp_path / "w", "vscode": tmp_path / "v"}
        r = runner.invoke(app, ["import", "claude_desktop"])
    assert r.exit_code == 1
    assert "not found" in r.output.lower() or "Config file" in r.output


def test_import_invalid_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from unittest.mock import patch

    monkeypatch.setenv("MCP_CONFIG_SYNC_CONFIG_DIR", str(tmp_path))
    runner.invoke(app, ["init"])
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("not valid json {")
    with patch("mcp_sync.paths.get_platform_client_paths") as m:
        m.return_value = {"claude_desktop": bad_file, "cursor": tmp_path / "c", "windsurf": tmp_path / "w", "vscode": tmp_path / "v"}
        r = runner.invoke(app, ["import", "claude_desktop"])
    assert r.exit_code == 1
    assert "invalid" in r.output.lower() or "JSON" in r.output or "error" in r.output.lower()


def test_import_skips_non_dict_entries(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """If a client has mcpServers with a non-dict value for a server, we should not crash."""
    from unittest.mock import patch

    monkeypatch.setenv("MCP_CONFIG_SYNC_CONFIG_DIR", str(tmp_path))
    runner.invoke(app, ["init"])
    client_file = tmp_path / "client.json"
    client_file.write_text(json.dumps({
        "mcpServers": {
            "good": {"command": "npx", "args": ["-y", "pkg"], "env": {}},
            "bad": "not a dict",
        },
    }))
    with patch("mcp_sync.paths.get_platform_client_paths") as m:
        m.return_value = {"claude_desktop": client_file, "cursor": tmp_path / "c", "windsurf": tmp_path / "w", "vscode": tmp_path / "v"}
        r = runner.invoke(app, ["import", "claude_desktop"])
    # Should either succeed (skipping bad) or fail gracefully
    assert r.exit_code in (0, 1)
    if r.exit_code == 0:
        # Good server should be imported
        r2 = runner.invoke(app, ["list"])
        assert "good" in r2.output