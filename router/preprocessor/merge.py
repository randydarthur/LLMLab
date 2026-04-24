# merge.py - merges common.yaml, agent.yaml, and env.yaml
def deep_merge(a, b):
    if not isinstance(a, dict) or not isinstance(b, dict):
        return b
    result = dict(a)
    for k, v in b.items():
        result[k] = deep_merge(a.get(k), v)
    return result
