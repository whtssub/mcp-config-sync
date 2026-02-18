"""CLI entry point for mcp-config-sync."""

import typer
from rich.console import Console

from mcp_sync.config import init_master_config, load_master_config
from mcp_sync.keyring_util import delete_all_keys_for_server, set_key
from mcp_sync.manager import parse_args_string

app = typer.Typer(
    name="mcp-config-sync",
    help="Unified CLI manager for MCP configurations. Write once, sync everywhere.",
)
console = Console()


def _ensure_init() -> None:
    from mcp_sync.paths import get_master_config_path
    if not get_master_config_path().exists():
        console.print("[red]Master config not found. Run [bold]mcp-config-sync init[/bold] first.[/red]")
        raise typer.Exit(1)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        console.print("[dim]Run [bold]mcp-config-sync --help[/bold] for commands.[/dim]")
        raise typer.Exit(0)


@app.command()
def init() -> None:
    """Create the platform-specific config directory and master config file (run first)."""
    path = init_master_config()
    console.print(f"[green]Initialized[/green] master config at [bold]{path}[/bold]")


@app.command("list")
def list_servers() -> None:
    """List currently managed servers."""
    _ensure_init()
    config = load_master_config()
    if not config.mcpServers:
        console.print("[dim]No servers in master config. Add with [bold]mcp-config-sync add <name>[/bold].[/dim]")
        return
    from rich.table import Table
    table = Table(title="Managed MCP servers")
    table.add_column("Name", style="cyan")
    table.add_column("Command", style="green")
    table.add_column("Args", style="dim")
    for name, entry in config.mcpServers.items():
        args_str = " ".join(entry.args) if entry.args else ""
        table.add_row(name, entry.command, args_str)
    console.print(table)


@app.command()
def add(
    name: str = typer.Argument(..., help="Server name (e.g. github)"),
    command: str = typer.Option(..., "--command", "-c", help="Executable (e.g. npx)"),
    args: str = typer.Option("", "--args", "-a", help="Arguments as string, parsed to list (e.g. '-y @modelcontextprotocol/server-github')"),
    env: list[str] = typer.Option([], "--env", "-e", help="Env key=value (non-secret)"),
    key: list[str] = typer.Option([], "--key", "-k", help="Env KEY=value stored in keyring (repeatable)"),
) -> None:
    """Add a server to the master list. Use --key for secrets (stored in system keychain)."""
    _ensure_init()
    from mcp_sync.config import add_server_to_master

    args_list = parse_args_string(args) if args else []
    env_dict: dict[str, str] = {}
    for pair in env:
        if "=" in pair:
            k, _, v = pair.partition("=")
            env_dict[k.strip()] = v.strip()
    keyring_keys: list[str] = []
    for pair in key:
        if "=" in pair:
            k, _, v = pair.partition("=")
            key_name = k.strip()
            keyring_keys.append(key_name)
            set_key(name, key_name, v.strip())
    add_server_to_master(name, command=command, args=args_list, env=env_dict or None, keyring_env_keys=keyring_keys or None)
    console.print(f"[green]Added[/green] server [bold]{name}[/bold].")


@app.command()
def remove(
    name: str = typer.Argument(..., help="Server name to remove"),
) -> None:
    """Remove a server from the master list and delete its keys from the keyring."""
    _ensure_init()
    from mcp_sync.config import remove_server_from_master

    entry = remove_server_from_master(name)
    if entry is None:
        console.print(f"[yellow]Server [bold]{name}[/bold] not in master config.[/yellow]")
        return
    delete_all_keys_for_server(name, entry.env_keys_from_keyring)
    console.print(f"[green]Removed[/green] server [bold]{name}[/bold].")


@app.command()
def wizard() -> None:
    """Interactive add: prompt for name, command, args, env, and optional keys."""
    _ensure_init()
    name = typer.prompt("Server name (e.g. github)")
    command = typer.prompt("Command (e.g. npx)", default="npx")
    args_str = typer.prompt("Arguments (e.g. -y @modelcontextprotocol/server-github)", default="")
    env_list: list[str] = []
    while True:
        e = typer.prompt("Env KEY=value (non-secret, or leave empty to skip)", default="")
        if not e:
            break
        env_list.append(e)
    key_list: list[str] = []
    while True:
        k = typer.prompt("Keyring KEY=value (secret, or leave empty to skip)", default="")
        if not k:
            break
        key_list.append(k)
    from mcp_sync.config import add_server_to_master
    args_list = parse_args_string(args_str) if args_str else []
    env_dict = {}
    for pair in env_list:
        if "=" in pair:
            k, _, v = pair.partition("=")
            env_dict[k.strip()] = v.strip()
    keyring_keys = []
    for pair in key_list:
        if "=" in pair:
            k, _, v = pair.partition("=")
            key_name = k.strip()
            keyring_keys.append(key_name)
            set_key(name, key_name, v.strip())
    add_server_to_master(name, command=command, args=args_list, env=env_dict or None, keyring_env_keys=keyring_keys or None)
    console.print(f"[green]Added[/green] server [bold]{name}[/bold].")


@app.command()
def sync(
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview what would be written; do not modify files"),
) -> None:
    """Push the master config to all detected client config files (with backup). Use --dry-run to preview."""
    _ensure_init()
    from mcp_sync.config import load_master_config
    from mcp_sync.keyring_util import get_keys_for_server
    from mcp_sync.manager import sync_client
    from mcp_sync.paths import get_detected_clients

    master = load_master_config()
    if not master.mcpServers:
        console.print("[yellow]No servers in master config. Add some with [bold]mcp-config-sync add[/bold].[/yellow]")
        raise typer.Exit(0)

    def get_keyring_env(server_name: str, env_keys: list[str]) -> dict[str, str]:
        return get_keys_for_server(server_name, env_keys)

    clients = get_detected_clients()
    if not clients:
        console.print("[yellow]No client config files found (Claude, Cursor, Windsurf, VS Code).[/yellow]")
        raise typer.Exit(0)

    if dry_run:
        console.print("[dim]Dry run: no files will be modified.[/dim]")
    from rich.table import Table
    table = Table(title="Sync results" + (" (dry-run)" if dry_run else ""))
    table.add_column("Client", style="cyan")
    table.add_column("Path", style="dim")
    table.add_column("Status", style="green")
    for client_id, path in clients:
        ok, msg = sync_client(path, master, get_keyring_env, dry_run=dry_run)
        status = f"[green]✓[/green] {msg}" if ok else f"[red]✗[/red] {msg}"
        table.add_row(client_id, str(path), status)
    console.print(table)


@app.command("import")
def import_cmd(
    client: str = typer.Argument(
        ...,
        help="Client to import from: claude_desktop, cursor, windsurf, vscode",
    ),
    store_keys: bool = typer.Option(False, "--store-keys", help="Prompt to store env values in keyring"),
) -> None:
    """Import servers from an existing client config into the master list."""
    _ensure_init()
    from mcp_sync.config import add_server_to_master, load_master_config
    from mcp_sync.paths import get_platform_client_paths

    paths = get_platform_client_paths()
    if client not in paths:
        console.print(f"[red]Unknown client [bold]{client}[/bold]. Choose: {', '.join(paths)}[/red]")
        raise typer.Exit(1)
    path = paths[client]
    if not path.exists():
        console.print(f"[red]Config file not found: [bold]{path}[/bold][/red]")
        raise typer.Exit(1)
    import json
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON in config file: [bold]{e}[/bold][/red]")
        raise typer.Exit(1)
    servers = data.get("mcpServers") or {}
    if not isinstance(servers, dict):
        servers = {}
    if not servers:
        console.print("[yellow]No mcpServers in that config.[/yellow]")
        raise typer.Exit(0)
    master = load_master_config()
    added = 0
    for name, entry in servers.items():
        if not isinstance(entry, dict):
            continue
        cmd = entry.get("command", "")
        args_list = entry.get("args") or []
        env = dict(entry.get("env") or {})
        keyring_keys: list[str] = []
        if store_keys and env:
            for k, v in env.items():
                if typer.confirm(f"Store [bold]{k}[/bold] in keyring for server [bold]{name}[/bold]?", default=False):
                    set_key(name, k, v)
                    keyring_keys.append(k)
        env_plain = {k: v for k, v in env.items() if k not in keyring_keys}
        add_server_to_master(name, command=cmd, args=args_list, env=env_plain or None, keyring_env_keys=keyring_keys or None)
        added += 1
    console.print(f"[green]Imported[/green] {added} server(s) from [bold]{client}[/bold].")


@app.command()
def status() -> None:
    """Show detected clients and whether they are in sync with the master config."""
    _ensure_init()
    from mcp_sync.config import load_master_config
    from mcp_sync.paths import get_detected_clients, get_platform_client_paths

    master = load_master_config()
    paths = get_platform_client_paths()
    from rich.table import Table
    table = Table(title="Client status")
    table.add_column("Client", style="cyan")
    table.add_column("Path", style="dim")
    table.add_column("Present", style="green")
    table.add_column("In sync", style="green")
    for client_id, path in paths.items():
        present = path.exists()
        in_sync = "[dim]—[/dim]"
        if present and master.mcpServers:
            try:
                import json
                data = json.loads(path.read_text(encoding="utf-8"))
                client_servers = (data.get("mcpServers") or {})
                missing = [n for n in master.mcpServers if n not in client_servers]
                wrong = []
                for n in master.mcpServers:
                    if n not in client_servers:
                        continue
                    ce = client_servers[n]
                    me = master.mcpServers[n]
                    if ce.get("command") != me.command or ce.get("args") != me.args:
                        wrong.append(n)
                if not missing and not wrong:
                    in_sync = "[green]✓[/green]"
                else:
                    in_sync = "[red]✗[/red]"
            except Exception:
                in_sync = "[red]error[/red]"
        elif not master.mcpServers:
            in_sync = "[dim]—[/dim]"
        table.add_row(client_id, str(path), "[green]✓[/green]" if present else "[red]—[/red]", in_sync)
    console.print(table)


if __name__ == "__main__":
    app()
