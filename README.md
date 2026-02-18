# mcp-config-sync

<p align="center">
  <img src="https://raw.githubusercontent.com/whtssub/mcp-sync/main/mcp-config-sync.png" alt="mcp-config-sync logo — cat on server stack" width="280">
</p>

**Keyring-secured** CLI for **MCP (Model Context Protocol)** config: one master list, sync to Claude Desktop, Cursor, VS Code, and Windsurf. API keys live in the system keychain, not in config files.

## Features

| What we have | Roadmap |
|--------------|---------|
| **Keyring-only secrets** — API keys stored in the system keychain and injected at sync time | **`sync --dry-run`** — preview what would be written per client (implemented) |
| **Single master config** — one list, sync to all clients | **`export [--redact]`** — dump master config for backup; `--redact` strips keyring key names/values so secrets never leave the machine |
| **Timestamped backup** before every sync write | **Secret detection** — warn when `--env` looks like a secret and suggest `--key` instead |
| **Windsurf, Claude Desktop, Cursor, VS Code** (user-level) | **Portable binary** — single executable so users don't need Python/uv |

## Install

```bash
# From PyPI (recommended)
pip install mcp-config-sync

# Or with uv
uv tool install mcp-config-sync

# From source
cd mcp-sync && uv sync && uv run mcp-config-sync --help
```

## Quick start

```bash
mcp-config-sync init
mcp-config-sync add github --command npx --args "-y @modelcontextprotocol/server-github" --key GITHUB_TOKEN=ghp_xxx
mcp-config-sync sync
```

## Commands

| Command | Description |
|--------|-------------|
| `mcp-config-sync init` | Create config directory and master config (run first). |
| `mcp-config-sync add <name>` | Add a server (use `--key KEY=value` for secrets in keyring). |
| `mcp-config-sync remove <name>` | Remove a server and its keys from keyring. |
| `mcp-config-sync sync` | Push master config to all detected clients (with backup). Use `--dry-run` to preview. |
| `mcp-config-sync list` | List managed servers. |
| `mcp-config-sync import <client>` | Import servers from a client (claude_desktop, cursor, windsurf, vscode). |
| `mcp-config-sync status` | Show which clients are present and in sync. |
| `mcp-config-sync wizard` | Interactive add with prompts. |

## Config location

- Master config: platform-specific (e.g. `~/.config/mcp-config-sync/master.json` on Linux, `~/Library/Application Support/mcp-config-sync/` on macOS).
- Override with `MCP_CONFIG_SYNC_CONFIG_DIR` for testing or a custom location.

## Development

```bash
uv sync --extra dev
uv run pytest
```

To build and publish to PyPI, see [PUBLISHING.md](PUBLISHING.md).

---

## Future scope

Planned and possible directions for mcp-config-sync:

- **Workspace / project-level sync** — Sync to Cursor's `.cursor/mcp.json` and VS Code's `.vscode/mcp.json` so teams can share MCP config via version control while still using a single source of truth.
- **More clients** — Auto-detect and support Code Insiders, Code OSS, and other editors as they add MCP config locations.
- **Distribution** — Homebrew tap for macOS, and packaging for Windows (e.g. winget) and Linux (e.g. .deb / .rpm or AUR).
- **Sync UX** — `mcp-config-sync sync --dry-run` (already implemented); optional watch mode or scheduled sync for keeping clients up to date.
- **Security** — Where clients allow it, keep secrets out of config files (e.g. env-only or keychain-backed injection); clearer warnings when keys are written to client JSON.
- **Portability** — Export/backup of the master config (with optional redaction of key names) for moving between machines or sharing templates.
- **MCP protocol** — Support for additional MCP transports or config shapes as the [Model Context Protocol](https://modelcontextprotocol.io/) spec evolves.

Contributions and ideas are welcome; open an issue or PR to discuss.

---

## License

MIT
