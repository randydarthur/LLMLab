# services/__init__.py

from ollama_lab.services.llm_backend_factory import get_llm_backend

# Single backend instance for the entire application
backend = get_llm_backend()

# Expose the unified API
is_available = backend.is_available
ensure_available = backend.ensure_available
list_models = backend.list_models
model_exists = backend.model_exists
pull_model = backend.pull_model
generate = backend.generate
generate_stream = backend.generate_stream
embed = backend.embed

__all__ = [
    "backend",
    "is_available",
    "ensure_available",
    "list_models",
    "model_exists",
    "pull_model",
    "generate",
    "generate_stream",
    "embed",
]

