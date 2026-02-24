"""Common utility functions."""

from typing import Any


def merge_configs(
    base_config: dict[str, Any], modifications: dict[str, Any]
) -> dict[str, Any]:
    """Deep merges modifications into a base configuration."""
    merged_config = base_config.copy()
    for key, value in modifications.items():
        if value is None:
            if key in merged_config:
                del merged_config[key]
        elif isinstance(value, dict) and isinstance(
            merged_config.get(key), dict
        ):
            merged_config[key] = merge_configs(merged_config[key], value)
        else:
            merged_config[key] = value
    return merged_config
