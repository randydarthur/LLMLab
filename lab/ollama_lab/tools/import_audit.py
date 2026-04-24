#!/usr/bin/env python3
"""
LLMLab Import Audit (descriptive version)

Checks:
  ✓ Absolute imports use ollama_lab.<submodule>...
  ✓ No legacy imports: models, services, utils, tui
  ✓ No relative imports
  ✓ No forbidden imports (registry → backend_factory)
  ✓ No double prefixes
  ✓ Reports file + line number + offending code
"""

import os
import ast
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = "ollama_lab"

FORBIDDEN = [
    (f"{PKG}.services.registry", f"{PKG}.services.llm_backend_factory"),
]

LEGACY_PREFIXES = ["models", "services", "utils", "tui"]


def iter_python_files():
    for root, dirs, files in os.walk(ROOT):
        if "venv" in root:
            continue
        for f in files:
            if f.endswith(".py"):
                yield os.path.join(root, f)


def module_name_from_path(path):
    rel = os.path.relpath(path, ROOT)
    parts = rel.split(os.sep)

    if parts[0] == "tools":
        return None

    if len(parts) == 1:
        return f"{PKG}.{parts[0][:-3]}"

    return f"{PKG}." + ".".join(
        [p[:-3] if p.endswith(".py") else p for p in parts]
    )


def audit_file(path, modname):
    issues = []

    try:
        with open(path, "r") as f:
            source = f.read()
            tree = ast.parse(source, filename=path)
    except Exception as e:
        return [f"AST parse error: {e}"]

    lines = source.splitlines()

    for node in ast.walk(tree):

        # ------------------------------
        # Relative imports
        # ------------------------------
        if isinstance(node, ast.ImportFrom) and node.level > 0:
            line = lines[node.lineno - 1].strip()
            issues.append({
                "type": "Relative import",
                "file": path,
                "line": node.lineno,
                "code": line,
            })

        # ------------------------------
        # Legacy imports
        # ------------------------------
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name

                for prefix in LEGACY_PREFIXES:
                    if name == prefix or name.startswith(prefix + "."):
                        line = lines[node.lineno - 1].strip()
                        issues.append({
                            "type": "Legacy import",
                            "file": path,
                            "line": node.lineno,
                            "code": line,
                        })

                if name.startswith(f"{PKG}.{PKG}."):
                    line = lines[node.lineno - 1].strip()
                    issues.append({
                        "type": "Double prefix",
                        "file": path,
                        "line": node.lineno,
                        "code": line,
                    })

        if isinstance(node, ast.ImportFrom):
            target = node.module or ""

            for prefix in LEGACY_PREFIXES:
                if target == prefix or target.startswith(prefix + "."):
                    line = lines[node.lineno - 1].strip()
                    issues.append({
                        "type": "Legacy import",
                        "file": path,
                        "line": node.lineno,
                        "code": line,
                    })

            if target.startswith(f"{PKG}.{PKG}."):
                line = lines[node.lineno - 1].strip()
                issues.append({
                    "type": "Double prefix",
                    "file": path,
                    "line": node.lineno,
                    "code": line,
                })

            # Forbidden imports
            for (src, forbidden) in FORBIDDEN:
                if modname == src and target.startswith(forbidden):
                    line = lines[node.lineno - 1].strip()
                    issues.append({
                        "type": "Forbidden import",
                        "file": path,
                        "line": node.lineno,
                        "code": line,
                    })

    return issues


def main():
    print("\n=== LLMLab Import Audit ===\n")

    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)

    all_issues = []

    for path in iter_python_files():
        modname = module_name_from_path(path)
        if not modname:
            continue

        issues = audit_file(path, modname)
        all_issues.extend(issues)

    if not all_issues:
        print("🎉 All imports are clean and absolute. No issues found.\n")
        return

    print("❌ Import issues detected:\n")

    for issue in all_issues:
        print(f"{issue['type']} in {issue['file']} at line {issue['line']}:")
        print(f"    {issue['code']}\n")

    print("⚠️  Audit completed with warnings.\n")


if __name__ == "__main__":
    main()

