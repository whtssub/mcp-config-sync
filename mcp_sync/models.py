"""Pydantic schemas for Master Config and Client Config (MCP JSON-RPC spec)."""

from pydantic import BaseModel, ConfigDict, Field


class MCPServerEntry(BaseModel):
    """Single MCP server entry: command, args array, optional env (non-secret)."""

    command: str
    args: list[str] = Field(default_factory=list, description="Arguments as list, e.g. ['-y', '@modelcontextprotocol/server-github']")
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables (non-secret); secrets go in keyring.")
    # Names of env vars stored in keyring (so we can delete them on remove). Not secret.
    env_keys_from_keyring: list[str] = Field(default_factory=list, alias="envKeysFromKeyring")

    model_config = {"populate_by_name": True}


class MasterConfig(BaseModel):
    """Source of truth: managed server list. No API keys stored here."""

    mcpServers: dict[str, MCPServerEntry] = Field(
        default_factory=dict,
        description="Server name -> server definition (command, args, env).",
    )


class ClientConfig(BaseModel):
    """Format MCP clients expect (Claude Desktop, Cursor, Windsurf, VS Code)."""

    model_config = ConfigDict(extra="allow")  # Clients may have other top-level keys (e.g. Claude)

    mcpServers: dict[str, MCPServerEntry] = Field(
        default_factory=dict,
        description="Server name -> server definition with command, args, env.",
    )
