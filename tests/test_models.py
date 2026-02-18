"""Tests for Pydantic models (Master Config, Client Config)."""

import pytest
from pydantic import ValidationError

from mcp_sync.models import ClientConfig, MasterConfig, MCPServerEntry


def test_mcpserver_entry_valid() -> None:
    e = MCPServerEntry(command="npx", args=["-y", "@x/server"], env={})
    assert e.command == "npx"
    assert e.args == ["-y", "@x/server"]
    assert e.env == {}


def test_mcpserver_entry_requires_command() -> None:
    with pytest.raises(ValidationError):
        MCPServerEntry(args=[])  # type: ignore


def test_mcpserver_entry_args_must_be_list() -> None:
    with pytest.raises(ValidationError):
        MCPServerEntry(command="npx", args="not a list")  # type: ignore


def test_master_config_empty() -> None:
    c = MasterConfig()
    assert c.mcpServers == {}


def test_master_config_with_servers() -> None:
    c = MasterConfig(mcpServers={"x": MCPServerEntry(command="npx", args=["-y", "pkg"])})
    assert "x" in c.mcpServers
    assert c.mcpServers["x"].command == "npx"


def test_client_config_extra_allowed() -> None:
    c = ClientConfig(mcpServers={}, some_other_key="allowed")  # type: ignore
    assert c.mcpServers == {}
