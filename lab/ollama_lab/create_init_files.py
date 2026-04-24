#!/usr/bin/env python3
import os

# Directories that must be Python packages
PACKAGE_DIRS = [
    ".",            # project root
    "models",
    "services",
    "tui",
    "utils",
]

INIT_CONTENT = "# Package marker for Python imports\n"

for d in PACKAGE_DIRS:
    init_path = os.path.join(d, "__init__.py")
    try:
        os.makedirs(d, exist_ok=True)
        if not os.path.exists(init_path):
            with open(init_path, "w") as f:
                f.write(INIT_CONTENT)
            print(f"Created: {init_path}")
        else:
            print(f"Exists:  {init_path}")
    except Exception as e:
        print(f"Error creating {init_path}: {e}")

