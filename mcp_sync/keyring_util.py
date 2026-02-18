"""Keyring helpers: store/retrieve/delete API keys per server. Service name: mcp-config-sync, username: {server_name}:{ENV_VAR}."""

import os
from typing import Optional

KEYRING_SERVICE = "mcp-config-sync"


def _username(server_name: str, env_var: str) -> str:
    return f"{server_name}:{env_var}"


def set_key(server_name: str, env_var: str, value: str) -> None:
    import keyring
    keyring.set_password(KEYRING_SERVICE, _username(server_name, env_var), value)


def get_key(server_name: str, env_var: str) -> Optional[str]:
    import keyring
    return keyring.get_password(KEYRING_SERVICE, _username(server_name, env_var))


def delete_key(server_name: str, env_var: str) -> None:
    import keyring
    keyring.delete_password(KEYRING_SERVICE, _username(server_name, env_var))


def delete_all_keys_for_server(server_name: str, env_var_names: list[str]) -> None:
    """Delete keyring entries for the given server and env var names."""
    for name in env_var_names:
        try:
            delete_key(server_name, name)
        except Exception:
            pass  # Ignore if key didn't exist


def get_keys_for_server(server_name: str, env_var_names: list[str]) -> dict[str, str]:
    """Return dict of env_var -> value for each key that exists in keyring."""
    result: dict[str, str] = {}
    for name in env_var_names:
        val = get_key(server_name, name)
        if val is not None:
            result[name] = val
    return result
