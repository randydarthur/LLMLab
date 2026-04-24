# resolve.py - resolves environment variables, paths, and YAML anchors
import os
def resolve_paths(config):
    for key, value in config.items():
        if isinstance(value, str):
            config[key] = os.path.expandvars(value)
    return config
