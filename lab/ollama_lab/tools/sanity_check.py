#!/usr/bin/env python3
"""
LLMLab Sanity Checker (package-aware, descriptive)

Checks:
  ✓ Import-time crashes
  ✓ Forbidden dependency directions
  ✓ Relative imports
  ✓ Legacy imports (models, services, utils, tui)
  ✓ Double prefixes (ollama_lab.ollama_lab)
  ✓ Reports file + line number + offending code
"""

import os
import sys
import ast
import importlib
import traceback

# ------------------------------------------------------------
# PATH SETUP
# ------------------------------------------------------------

# Directory containing this file: .../ollama_lab/tools
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))

# Project root: .../ollama_lab
PROJECT_ROOT = os.path.dirname(TOOLS_DIR)

# Parent directory: .../ (this must be on sys.path)
PARENT = os.path.dirname(PROJECT_ROOT)

if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

PKG = "ollama_lab"

# Forbidden import patterns
FORBIDDEN = [
    (f"{PKG}.services.registry", f"{PKG}.services.llm_backend_factory"),
]

LEGACY_PREFIXES = ["models", "services", "utils", "tui"]


# ------------------------------------------------------------
# FILE DISCOVERY
# ------------------------------------------------------------

def iter_python_files():
    """Yield all .py files under the project root (excluding venv)."""
    for root, dirs, files in os.walk(PROJECT_ROOT):
        if "venv" in root:
            continue
        for f in files:
            if f.endswith(".py"):
                yield os.path.join(root, f)


def module_name_from_path(path):
    """Convert a file path into a module name under ollama_lab.*"""
    rel = os.path.relpath(path, PROJECT_ROOT)
    parts = rel.split(os.sep)

    # Skip tools/ itself
    if parts[0] == "tools":
        return None

    # Root-level modules (main.py, repl.py, etc.)
    if len(parts) == 1:
        return f"{PKG}.{parts[0][:-3]}"

    # Package modules
    return f"{PKG}." + ".".join(
        [p[:-3] if p.endswith(".py") else p for p in parts]
    )


# ------------------------------------------------------------
# IMPORT ANALYSIS
# ------------------------------------------------------------

def analyze_imports(path, modname):
    """Return a list of issues found in a file."""
    issues = []

    try:
        with open(path, "r") as f:
            source = f.read()
            tree = ast.parse(source, filename=path)
    except Exception as e:
        return [{
            "type": "AST parse error",
            "file": path,
            "line": 0,
            "code": str(e),
        }]

    lines = source.splitlines()

    for node in ast.walk(tree):

        # ------------------------------
        # Relative imports
        # ------------------------------
        if isinstance(node, ast.ImportFrom) and node.level > 0:
            issues.append({
                "type": "Relative import",
                "file": path,
                "line": node.lineno,
                "code": lines[node.lineno - 1].strip(),
            })

        # ------------------------------
        # Legacy imports
        # ------------------------------
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name

                for prefix in LEGACY_PREFIXES:
                    if name == prefix or name.startswith(prefix + "."):
                        issues.append({
                            "type": "Legacy import",
                            "file": path,
                            "line": node.lineno,
                            "code": lines[node.lineno - 1].strip(),
                        })

                if name.startswith(f"{PKG}.{PKG}."):
                    issues.append({
                        "type": "Double prefix",
                        "file": path,
                        "line": node.lineno,
                        "code": lines[node.lineno - 1].strip(),
                    })

        if isinstance(node, ast.ImportFrom):
            target = node.module or ""

            for prefix in LEGACY_PREFIXES:
                if target == prefix or target.startswith(prefix + "."):
                    issues.append({
                        "type": "Legacy import",
                        "file": path,
                        "line": node.lineno,
                        "code": lines[node.lineno - 1].strip(),
                    })

            if target.startswith(f"{PKG}.{PKG}."):
                issues.append({
                    "type": "Double prefix",
                    "file": path,
                    "line": node.lineno,
                    "code": lines[node.lineno - 1].strip(),
                })

            # Forbidden imports
            for (src, forbidden) in FORBIDDEN:
                if modname == src and target.startswith(forbidden):
                    issues.append({
                        "type": "Forbidden import",
                        "file": path,
                        "line": node.lineno,
                        "code": lines[node.lineno - 1].strip(),
                    })

    return issues


# ------------------------------------------------------------
# MAIN CHECKER
# ------------------------------------------------------------

def run_sanity_check():
    print("\n=== LLMLab Sanity Check ===\n")

    import_errors = []
    import_issues = []

    for path in iter_python_files():
        modname = module_name_from_path(path)
        if not modname:
            continue

        # Static import analysis
        issues = analyze_imports(path, modname)
        import_issues.extend(issues)

        # Import-time errors
        try:
            importlib.import_module(modname)
        except Exception as e:
            import_errors.append({
                "module": modname,
                "file": path,
                "error": "".join(traceback.format_exception_only(type(e), e)).strip(),
            })

    # --------------------------------------------------------
    # REPORTING
    # --------------------------------------------------------

    if import_errors:
        print("❌ Import-time failures detected:\n")
        for err in import_errors:
            print(f"  {err['module']}  (file: {err['file']})")
            print(f"    {err['error']}\n")

    if import_issues:
        print("❌ Import issues detected:\n")
        for issue in import_issues:
            print(f"{issue['type']} in {issue['file']} at line {issue['line']}:")
            print(f"    {issue['code']}\n")

    if not import_errors and not import_issues:
        print("🎉 All sanity checks passed. Structure looks clean.\n")
    else:
        print("⚠️  Sanity check completed with warnings.\n")


if __name__ == "__main__":
    run_sanity_check()

