#!/usr/bin/env bash
set -e

echo "=== Fixing stale imports in LLMLab (bulletproof mode) ==="

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PKG_DIR="$PROJECT_ROOT"

echo "Project root: $PROJECT_ROOT"
echo "Package dir:  $PKG_DIR"

# Helper: safe sed for macOS + Linux
sedi() {
    if sed --version >/dev/null 2>&1; then
        sed -i "$@"
    else
        sed -i '' "$@"
    fi
}

echo
echo "--- Removing ANY form of 'register_model' import ---"
grep -RIn "register_model" "$PKG_DIR" | grep -v "fix_imports.sh" || true | while read -r line; do
    file="${line%%:*}"
    echo "Fixing import in: $file"
    sedi 's/.*register_model.*//g' "$file"
done

echo
echo "--- Replacing ANY call to register_model(...) ---"
grep -RIn "register_model" "$PKG_DIR" | grep -v "fix_imports.sh" || true | while read -r line; do
    file="${line%%:*}"
    echo "Fixing call site in: $file"
    sedi 's/register_model\s*(\s*[^)]*)/rebuild_registry_from_backend(backend)/g' "$file"
done

echo
echo "--- Fixing ANY form of 'list_services' import ---"
grep -RIn "list_services" "$PKG_DIR" | grep -v "fix_imports.sh" || true | while read -r line; do
    file="${line%%:*}"
    echo "Fixing: $file"
    sedi 's/list_services/list_models/g' "$file"
done

echo
echo "--- Fixing ANY form of 'import model_intelligence' ---"
grep -RIn "model_intelligence" "$PKG_DIR" | grep -v "fix_imports.sh" || true | while read -r line; do
    file="${line%%:*}"
    echo "Fixing: $file"
    sedi 's/import model_intelligence/from ollama_lab import model_intelligence/g' "$file"
done

echo
echo "=== Import fixes complete ==="

