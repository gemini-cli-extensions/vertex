"""Common utility functions."""

from typing import Any

import vertexai


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


def _get_optimization_target(method: str) -> vertexai.types.OptimizeTarget:
    """Returns the optimization target for the given method."""
    if method == "TARGET_RESPONSE":
        return vertexai.types.OptimizeTarget.OPTIMIZATION_TARGET_FEW_SHOT_TARGET_RESPONSE
    elif method == "RUBRICS":
        return (
            vertexai.types.OptimizeTarget.OPTIMIZATION_TARGET_FEW_SHOT_RUBRICS
        )
    else:
        raise ValueError(f"Unsupported optimization method: {method}")
