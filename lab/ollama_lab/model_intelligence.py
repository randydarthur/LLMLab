#!/usr/bin/env python3
"""
Model Intelligence Layer (MIL)
------------------------------

This module integrates llmfit into the Lab Manager to provide:

- Hardware profiling
- Recommended models (hardware-aware)
- Fit scoring for installed models
- Model metadata enrichment
- Quantization recommendations
- Comprehensive benchmarking

All functions gracefully degrade if llmfit is not installed.
"""

import subprocess
import json
import shutil
import os

# ============================================================
# LLMFIT BINARY DISCOVERY
# ============================================================

LLMFIT = shutil.which("llmfit")

# Fallback to ~/.local/bin
if not LLMFIT:
    candidate = os.path.expanduser("~/.local/bin/llmfit")
    if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
        LLMFIT = candidate

if not LLMFIT:
    print("[model_intelligence] WARNING: llmfit not found. MIL disabled.")


# ============================================================
# MODEL NAME NORMALIZATION (Ollama → HuggingFace)
# ============================================================

MODEL_NAME_MAP = {
    "qwen2.5": "Qwen/Qwen2.5-7B-Instruct-GPTQ-Int4",
    "mistral": "mistralai/Mistral-7B-Instruct-v0.3",
    "phi3": None,
    "gemma2": "hmellor/tiny-random-Gemma2ForCausalLM",
    "codegemma": "google/gemma-2-9b-it",
    "starling": None,
    "llama3.2": "meta-llama/Llama-3.2-3B",
    "deepseek": "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B",
}

def normalize_model_name(ollama_repo: str):
    base = ollama_repo.split(":")[0].lower()
    return MODEL_NAME_MAP.get(base)


# ============================================================
# INTERNAL HELPER — SAFE LLMFIT EXECUTION
# ============================================================

def _run_llmfit(args):
    """
    Safely run llmfit with the given argument list.
    Returns parsed JSON or None on failure.
    """
    if not LLMFIT:
        return None

    cmd = [LLMFIT, "--cli", "--json"] + args

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            return None
        if not result.stdout.strip():
            return None
        return json.loads(result.stdout)
    except Exception:
        return None


# ============================================================
# HARDWARE PROFILE
# ============================================================

def get_hardware_profile():
    data = _run_llmfit(["system"])
    if not data:
        return {
            "backend": None,
            "gpu_vram_gb": None,
            "cpu_name": None,
            "gpu_name": None,
            "total_ram_gb": None,
            "available_ram_gb": None,
        }

    # unwrap llmfit's "system" wrapper
    return data.get("system", {})


# ============================================================
# RECOMMENDED MODELS (ALL PROVIDERS)
# ============================================================

def _get_all_recommended_models():
    data = _run_llmfit(["recommend"])
    if not data:
        return []
    return data.get("models", [])


# ============================================================
# RECOMMENDED MODELS (Ollama-compatible subset)
# ============================================================

def get_recommended_ollama_models():
    """
    Returns recommended models that have a mapping to an Ollama repo.
    """
    all_models = _get_all_recommended_models()
    mapped = set(MODEL_NAME_MAP.values()) - {None}
    return [m for m in all_models if m.get("name") in mapped]


def get_marginal_ollama_models(installed_repos=None):
    if installed_repos is None:
        installed_repos = set()

    all_models = _get_all_recommended_models()
    mapped = set(MODEL_NAME_MAP.values()) - {None}

    marginal = []
    for m in all_models:
        name = m.get("name")
        if name not in mapped:
            continue

        repo = None
        for k, v in MODEL_NAME_MAP.items():
            if v == name:
                repo = k
                break

        if not repo or repo in installed_repos:
            continue

        fit = m.get("fit_score")
        if fit is None or fit <= 0:
            continue

        marginal.append(m)

    return marginal


# ============================================================
# MODEL METADATA
# ============================================================

def get_model_metadata(model_name):
    hf_name = normalize_model_name(model_name)
    if not hf_name:
        return None

    data = _run_llmfit(["catalog"])
    if not data:
        return None

    for m in data.get("models", []):
        if m.get("name") == hf_name:
            return m

    return None


# ============================================================
# FIT SCORE / CONTEXT / QUANTIZATION
# ============================================================

def get_fit_score(model_name):
    meta = get_model_metadata(model_name)
    return meta.get("fit_score") if meta else None


def get_quantization_recommendation(model_name):
    meta = get_model_metadata(model_name)
    return meta.get("recommended_quant") if meta else None


def get_context_window(model_name):
    meta = get_model_metadata(model_name)
    return meta.get("context") if meta else None


# ============================================================
# BENCHMARKING
# ============================================================

def benchmark_model(model_name, port):
    hf_name = normalize_model_name(model_name)
    if not hf_name:
        return None

    return _run_llmfit(["benchmark", hf, "--host", f"127.0.0.1:{port}"])


# ============================================================
# SUMMARY API FOR TUI
# ============================================================

def summarize_model(model_name):
    meta = get_model_metadata(model_name)
    if not meta:
        return {
            "fit_score": None,
            "recommended_quant": None,
            "context": None,
            "size_gb": None,
            "quality_tier": None,
            "speed_tier": None,
            "provider": None,
        }

    return {
        "fit_score": meta.get("fit_score"),
        "recommended_quant": meta.get("recommended_quant"),
        "context": meta.get("context"),
        "size_gb": meta.get("size_gb"),
        "quality_tier": meta.get("quality_tier"),
        "speed_tier": meta.get("speed_tier"),
        "provider": meta.get("provider"),
    }

