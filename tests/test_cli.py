"""CLI tests using Typer CliRunner with isolated config dir."""

import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from mcp_sync.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolated_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MCP_CONFIG_SYNC_CONFIG_DIR", str(tmp_path))


def test_cli_help(isolated_config: None) -> None:
    r = runner.invoke(app, ["--help"])
    assert r.exit_code == 0
    assert "init" in r.output
    assert "add" in r.output
    assert "sync" in r.output


def test_init_creates_master_json(tmp_path: Path) -> None:
    r = runner.invoke(app, ["init"])
    assert r.exit_code == 0
    assert (tmp_path / "master.json").exists()


def test_list_without_init_fails() -> None:
    """List fails when master.json does not exist (fixture uses empty tmp_path)."""
    r = runner.invoke(app, ["list"])
    assert r.exit_code == 1
    assert "init" in r.output


def test_add_then_list(tmp_path: Path) -> None:
    runner.invoke(app, ["init"])
    r = runner.invoke(app, ["add", "github", "--command", "npx", "--args", "-y @mcp/server-github"])
    assert r.exit_code == 0
    r2 = runner.invoke(app, ["list"])
    assert r2.exit_code == 0
    assert "github" in r2.output
    assert "npx" in r2.output


def test_add_with_env_value_containing_equals(tmp_path: Path) -> None:
    """Env and key options support values containing '=' (partition on first =)."""
    runner.invoke(app, ["init"])
    r = runner.invoke(app, ["add", "eq", "--command", "npx", "--args", "", "--env", "FOO=bar=baz"])
    assert r.exit_code == 0
    from mcp_sync.config import load_master_config
    config = load_master_config()
    assert config.mcpServers["eq"].env.get("FOO") == "bar=baz"


def test_remove_then_list(tmp_path: Path) -> None:
    runner.invoke(app, ["init"])
    runner.invoke(app, ["add", "x", "--command", "npx", "--args", ""])
    r = runner.invoke(app, ["remove", "x"])
    assert r.exit_code == 0
    r2 = runner.invoke(app, ["list"])
    assert r2.exit_code == 0
    assert "No servers" in r2.output or "x" not in r2.output
