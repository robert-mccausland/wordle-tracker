import os


def _get_env(name: str, default: str | None = None) -> str:
    value = os.getenv(name) or default
    assert value is not None, f"Expected {name} environment variable to be provided"
    return value


def _get_env_int(name: str, default: int | None = None) -> int:
    value = os.getenv(name)
    if value is None:
        assert default is not None, f"Expected {name} environment variable to be provided"
        return default
    try:
        return int(value)
    except ValueError:
        raise ValueError(f"Environment variable {name} must be an integer, got '{value}'")


def _get_env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        assert default is not None, f"Expected {name} environment variable to be provided"
        return default

    v = value.strip().upper()
    if v == "TRUE":
        return True
    elif v == "FALSE":
        return False
    else:
        raise ValueError(f"Environment variable {name} must be a boolean ('TRUE' or 'FALSE'), got '{value}'")


TOKEN = _get_env("TOKEN")
SUMMARY_LIMIT_DEFAULT = _get_env_int("SUMMARY_LIMIT_DEFAULT", 5)
USERNAME_MAX_LENGTH = _get_env_int("USERNAME_MAX_LENGTH", 12)
CLIENT_WAIT_TIMEOUT = _get_env_int("CLIENT_WAIT_TIMEOUT", 60)
SYNC_COMMANDS = _get_env_bool("SYNC_COMMANDS", True)
