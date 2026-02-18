"""Core logic: add/remove servers, keyring, sync (Phase 2–3)."""

import json
from datetime import datetime
from pathlib import Path
from typing import Callable

from mcp_sync.models import MasterConfig, MCPServerEntry


def parse_args_string(s: str) -> list[str]:
    """Parse --args string into a list (split on spaces, respect quotes)."""
    if not s or not s.strip():
        return []
    result: list[str] = []
    current: list[str] = []
    in_quote = False
    quote_char = '"'
    for c in s:
        if in_quote:
            if c == quote_char:
                in_quote = False
                result.append("".join(current))
                current = []
            else:
                current.append(c)
        elif c in "\"\'":
            in_quote = True
            quote_char = c
            if current:
                result.append("".join(current))
                current = []
        elif c.isspace():
            if current:
                result.append("".join(current))
                current = []
        else:
            current.append(c)
    if current:
        result.append("".join(current))
    return result


def backup_client_config(client_path: Path) -> Path | None:
    """Create a timestamped backup of the client config file. Returns backup path or None if no file."""
    if not client_path.exists():
        return None
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    backup_path = client_path.with_suffix(client_path.suffix + f".{stamp}.bak")
    backup_path.write_text(client_path.read_text(encoding="utf-8"), encoding="utf-8")
    return backup_path


def merge_master_into_client(
    client_path: Path,
    master: MasterConfig,
    get_keyring_env: Callable[[str, list[str]], dict[str, str]],
) -> dict:
    """
    Read client JSON, upsert mcpServers from master (inject keyring into env), leave others untouched.
    Returns the merged dict (full file content) for validation and write.
    """
    if client_path.exists():
        data = json.loads(client_path.read_text(encoding="utf-8"))
    else:
        data = {}
    servers = data.get("mcpServers")
    if not isinstance(servers, dict):
        servers = {}

    for name, entry in master.mcpServers.items():
        env = dict(entry.env)
        if entry.env_keys_from_keyring:
            keyring_vals = get_keyring_env(name, entry.env_keys_from_keyring)
            env.update(keyring_vals)
        servers[name] = {
            "command": entry.command,
            "args": entry.args,
            "env": env,
        }
    data["mcpServers"] = servers
    return data


def write_client_config(client_path: Path, data: dict) -> None:
    """Validate and write client config JSON. Creates parent dirs if needed."""
    client_path.parent.mkdir(parents=True, exist_ok=True)
    client_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def sync_client(
    client_path: Path,
    master: MasterConfig,
    get_keyring_env: Callable[[str, list[str]], dict[str, str]],
    dry_run: bool = False,
) -> tuple[bool, str]:
    """
    Merge master into client; write unless dry_run. Returns (success, message).
    When dry_run=True, no backup or file write is performed.
    """
    try:
        merged = merge_master_into_client(client_path, master, get_keyring_env)
        if dry_run:
            return True, "Would sync (dry-run)"
        backup_client_config(client_path)
        write_client_config(client_path, merged)
        return True, "Synced"
    except Exception as e:
        return False, str(e)
