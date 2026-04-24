# core/read_configs.py

import yaml
from pathlib import Path
from typing import Dict, Any


class ConfigLoader:
    """
    Loads and merges YAML configuration files from the router/configs directory.

    This module provides a single entrypoint:
        load_router_config(config_dir: str | Path) -> Dict[str, Any]

    The returned dictionary is passed directly into:
        - ModelRegistry
        - TaskClassifier
        - RoutingEngine
        - BackendFactory
    """

    @staticmethod
    def load_router_config(config_dir: str | Path) -> Dict[str, Any]:
        """
        Load all YAML files in the given directory and merge them into a single config dict.

        Expected files:
            backends.yaml
            tasks.yaml
            routing.yaml

        Returns:
            A merged configuration dictionary.
        """
        config_dir = Path(config_dir)
        if not config_dir.exists():
            raise FileNotFoundError(f"Config directory not found: {config_dir}")

        merged: Dict[str, Any] = {}

        for file in sorted(config_dir.glob("*.yaml")):
            with open(file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                merged = ConfigLoader._deep_merge(merged, data)

        return merged

    @staticmethod
    def _deep_merge(base: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively merge two dictionaries.
        Values in `new` override values in `base`.
        """
        for key, value in new.items():
            if (
                key in base
                and isinstance(base[key], dict)
                and isinstance(value, dict)
            ):
                base[key] = ConfigLoader._deep_merge(base[key], value)
            else:
                base[key] = value
        return base

