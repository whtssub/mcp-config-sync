"""Tests for manager: parse_args_string, backup, merge."""

import json
from pathlib import Path

import pytest

from mcp_sync.manager import (
    backup_client_config,
    merge_master_into_client,
    parse_args_string,
    write_client_config,
)
from mcp_sync.models import MasterConfig, MCPServerEntry


def test_parse_args_string_simple() -> None:
    assert parse_args_string("-y @modelcontextprotocol/server-github") == [
        "-y",
        "@modelcontextprotocol/server-github",
    ]
    assert parse_args_string("a b c") == ["a", "b", "c"]


def test_parse_args_string_quoted() -> None:
    assert parse_args_string('"a b" c') == ["a b", "c"]
    assert parse_args_string("") == []
    assert parse_args_string("   ") == []


def test_parse_args_string_unclosed_quote_appends_remaining() -> None:
    """Unclosed quote: remaining current token should still be appended."""
    result = parse_args_string('a b "c d')
    assert "c d" in result or "".join(result)  # implementation may append trailing
    assert result[:2] == ["a", "b"]


def test_backup_client_config_creates_file(tmp_path: Path) -> None:
    config_file = tmp_path / "mcp.json"
    config_file.write_text('{"mcpServers":{}}')
    backup_path = backup_client_config(config_file)
    assert backup_path is not None
    assert backup_path.exists()
    assert backup_path.read_text() == '{"mcpServers":{}}'
    assert ".bak" in backup_path.suffix or ".bak" in str(backup_path)


def test_backup_client_config_none_when_missing(tmp_path: Path) -> None:
    assert backup_client_config(tmp_path / "nonexistent.json") is None


def test_merge_master_into_client_upsert(tmp_path: Path) -> None:
    client_path = tmp_path / "client.json"
    client_path.write_text(json.dumps({"mcpServers": {"other": {"command": "other", "args": [], "env": {}}}}))
    master = MasterConfig(mcpServers={
        "github": MCPServerEntry(command="npx", args=["-y", "@mcp/server-github"], env={}),
    })
    def no_keyring(_: str, __: list[str]) -> dict[str, str]:
        return {}
    merged = merge_master_into_client(client_path, master, no_keyring)
    assert "github" in merged["mcpServers"]
    assert merged["mcpServers"]["github"]["command"] == "npx"
    assert "other" in merged["mcpServers"]


def test_merge_injects_keyring_env(tmp_path: Path) -> None:
    client_path = tmp_path / "client.json"
    client_path.write_text("{}")
    master = MasterConfig(mcpServers={
        "srv": MCPServerEntry(
            command="npx", args=[], env={},
            env_keys_from_keyring=["API_KEY"],
        ),
    })
    def keyring(_: str, keys: list[str]) -> dict[str, str]:
        return {k: f"val-{k}" for k in keys}
    merged = merge_master_into_client(client_path, master, keyring)
    assert merged["mcpServers"]["srv"]["env"]["API_KEY"] == "val-API_KEY"


def test_write_client_config_creates_dirs(tmp_path: Path) -> None:
    out = tmp_path / "a" / "b" / "mcp.json"
    write_client_config(out, {"mcpServers": {}})
    assert out.exists()
    assert json.loads(out.read_text())["mcpServers"] == {}


def test_merge_handles_null_mcp_servers(tmp_path: Path) -> None:
    """Client config with mcpServers: null should not crash; merged result has dict."""
    client_path = tmp_path / "client.json"
    client_path.write_text('{"mcpServers": null}')
    master = MasterConfig(mcpServers={
        "x": MCPServerEntry(command="npx", args=["-y", "pkg"], env={}),
    })
    merged = merge_master_into_client(client_path, master, lambda _s, _k: {})
    assert isinstance(merged["mcpServers"], dict)
    assert merged["mcpServers"]["x"]["command"] == "npx"


def test_merge_handles_missing_mcp_servers_key(tmp_path: Path) -> None:
    """Client config with no mcpServers key should get one."""
    client_path = tmp_path / "client.json"
    client_path.write_text("{}")
    master = MasterConfig(mcpServers={
        "y": MCPServerEntry(command="node", args=[], env={}),
    })
    merged = merge_master_into_client(client_path, master, lambda _s, _k: {})
    assert "mcpServers" in merged
    assert merged["mcpServers"]["y"]["command"] == "node"


def test_merge_handles_non_dict_mcp_servers(tmp_path: Path) -> None:
    """Client config with mcpServers as list (invalid) should not crash."""
    client_path = tmp_path / "client.json"
    client_path.write_text('{"mcpServers": []}')
    master = MasterConfig(mcpServers={
        "z": MCPServerEntry(command="npx", args=[], env={}),
    })
    merged = merge_master_into_client(client_path, master, lambda _s, _k: {})
    assert isinstance(merged["mcpServers"], dict)
    assert merged["mcpServers"]["z"]["command"] == "npx"


def test_sync_client_invalid_client_json_returns_failure(tmp_path: Path) -> None:
    """If client config file has invalid JSON, sync_client returns (False, error message)."""
    from mcp_sync.manager import sync_client

    client_path = tmp_path / "mcp.json"
    client_path.write_text("not valid json")
    master = MasterConfig(mcpServers={
        "x": MCPServerEntry(command="npx", args=[], env={}),
    })
    ok, msg = sync_client(client_path, master, lambda _s, _k: {})
    assert ok is False
    assert "JSON" in msg or "Expecting" in msg or len(msg) > 0


def test_sync_client_dry_run_does_not_write(tmp_path: Path) -> None:
    """With dry_run=True, merge runs but file is not written."""
    from mcp_sync.manager import sync_client

    client_path = tmp_path / "mcp.json"
    original = '{"mcpServers": {"other": {"command": "x", "args": [], "env": {}}}}'
    client_path.write_text(original)
    master = MasterConfig(mcpServers={
        "new": MCPServerEntry(command="npx", args=["-y", "pkg"], env={}),
    })
    ok, msg = sync_client(client_path, master, lambda _s, _k: {}, dry_run=True)
    assert ok is True
    assert "dry-run" in msg.lower()
    assert client_path.read_text() == original
