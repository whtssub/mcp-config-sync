"""Internal config management: master.json read/write and init."""

import json
from pathlib import Path

from mcp_sync.keyring_util import delete_all_keys_for_server
from mcp_sync.models import MasterConfig, MCPServerEntry
from mcp_sync.paths import get_master_config_dir, get_master_config_path


def ensure_master_config_dir() -> Path:
    """Create platform-specific config directory if it does not exist. Return its path."""
    d = get_master_config_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d


def init_master_config() -> Path:
    """Create config dir and empty master.json if missing. Return path to master.json."""
    ensure_master_config_dir()
    path = get_master_config_path()
    if not path.exists():
        path.write_text(MasterConfig().model_dump_json(indent=2), encoding="utf-8")
    return path


def load_master_config() -> MasterConfig:
    """Load master config from disk. Returns empty config if file missing or invalid."""
    path = get_master_config_path()
    if not path.exists():
        return MasterConfig()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return MasterConfig.model_validate(data)
    except Exception:
        return MasterConfig()


def save_master_config(config: MasterConfig) -> None:
    """Write master config to disk."""
    path = get_master_config_path()
    ensure_master_config_dir()
    path.write_text(config.model_dump_json(indent=2, by_alias=True), encoding="utf-8")


def add_server_to_master(
    name: str,
    command: str,
    args: list[str],
    env: dict[str, str] | None = None,
    keyring_env_keys: list[str] | None = None,
) -> None:
    """Add or overwrite a server in master config. Does not write keyring (caller does). Removes from keyring any keys that were in the old entry but not in the new list."""
    config = load_master_config()
    new_keys = set(keyring_env_keys or [])
    old_entry = config.mcpServers.get(name)
    if old_entry and old_entry.env_keys_from_keyring:
        to_remove = [k for k in old_entry.env_keys_from_keyring if k not in new_keys]
        if to_remove:
            delete_all_keys_for_server(name, to_remove)
    entry = MCPServerEntry(
        command=command,
        args=args,
        env=dict(env or {}),
        env_keys_from_keyring=list(keyring_env_keys or []),
    )
    config.mcpServers[name] = entry
    save_master_config(config)


def remove_server_from_master(name: str) -> MCPServerEntry | None:
    """Remove server from master config. Returns the removed entry (so caller can clean keyring)."""
    config = load_master_config()
    entry = config.mcpServers.pop(name, None)
    if entry is not None:
        save_master_config(config)
    return entry
