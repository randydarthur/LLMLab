psutil = None
try:
    import psutil
except ImportError:
    pass

def get_system_ram():
    mem = psutil.virtual_memory()
    return mem.total, mem.available

def get_cpu_load():
    try:
        return psutil.cpu_percent(interval=0.1)
    except Exception:
        return None

def get_gpu_load():
    # Placeholder: no GPU metrics available on this system
    # You can integrate nvidia-smi or ROCm later
    return None

