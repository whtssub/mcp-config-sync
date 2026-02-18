"""OS-specific path resolution for MCP client config files."""

import os
from pathlib import Path

from platformdirs import user_config_dir

# App name for mcp-config-sync's own config
APP_NAME = "mcp-config-sync"

# Client identifiers
CLAUDE_DESKTOP = "claude_desktop"
CURSOR = "cursor"
WINDSURF = "windsurf"
VSCODE = "vscode"

# (client_id, path_template or callable for expansion)
# Use Path.expanduser() and os.path.expandvars() when resolving.
def _home() -> Path:
    return Path.home()


def _appdata() -> str:
    return os.environ.get("APPDATA", os.path.expanduser("~\\AppData\\Roaming"))


def _userprofile() -> str:
    return os.environ.get("USERPROFILE", os.path.expanduser("~"))


def get_platform_client_paths() -> dict[str, Path]:
    """Return client_id -> absolute Path for this OS. Paths may not exist."""
    paths: dict[str, Path] = {}
    if os.name == "nt":
        # Windows
        paths[CLAUDE_DESKTOP] = Path(_appdata()) / "Claude" / "claude_desktop_config.json"
        paths[CURSOR] = Path(_userprofile()) / ".cursor" / "mcp.json"
        paths[WINDSURF] = Path(_userprofile()) / ".codeium" / "windsurf" / "mcp_config.json"
        paths[VSCODE] = Path(_appdata()) / "Code" / "User" / "mcp.json"
    else:
        # macOS vs Linux
        is_darwin = os.uname().sysname == "Darwin"
        paths[CURSOR] = _home() / ".cursor" / "mcp.json"
        paths[WINDSURF] = _home() / ".codeium" / "windsurf" / "mcp_config.json"
        if is_darwin:
            paths[CLAUDE_DESKTOP] = _home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
            paths[VSCODE] = _home() / "Library" / "Application Support" / "Code" / "User" / "mcp.json"
        else:
            paths[CLAUDE_DESKTOP] = _home() / ".config" / "Claude" / "claude_desktop_config.json"
            paths[VSCODE] = _home() / ".config" / "Code" / "User" / "mcp.json"
    return paths


def get_master_config_dir() -> Path:
    """Platform-specific mcp-config-sync config directory (e.g. ~/.config/mcp-config-sync on Linux). Override with MCP_CONFIG_SYNC_CONFIG_DIR."""
    if os.environ.get("MCP_CONFIG_SYNC_CONFIG_DIR"):
        return Path(os.environ["MCP_CONFIG_SYNC_CONFIG_DIR"]).expanduser().resolve()
    return Path(user_config_dir(APP_NAME))


def get_master_config_path() -> Path:
    """Path to master.json (source of truth)."""
    return get_master_config_dir() / "master.json"


def get_detected_clients() -> list[tuple[str, Path]]:
    """Return list of (client_id, config_path) for clients whose config file exists."""
    all_paths = get_platform_client_paths()
    return [(cid, p) for cid, p in all_paths.items() if p.exists()]
