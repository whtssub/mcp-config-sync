"""CLI tests using Typer CliRunner with isolated config dir."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from mcp_sync.cli import app
from mcp_sync.paths import get_master_config_path

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


def test_cli_version(isolated_config: None) -> None:
    r = runner.invoke(app, ["--version"])
    assert r.exit_code == 0
    assert "mcp-config-sync" in r.output
    assert "0.1.0" in r.output


def test_init_creates_master_json() -> None:
    """Init creates master.json in the dir given by MCP_CONFIG_SYNC_CONFIG_DIR (set by isolated_config)."""
    r = runner.invoke(app, ["init"])
    assert r.exit_code == 0
    assert get_master_config_path().exists()


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
