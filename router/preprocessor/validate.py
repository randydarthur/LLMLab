# validate.py - validates merged agent config against schema.yaml
def validate(config, schema):
    missing = [key for key in schema.get("required", []) if key not in config]
    if missing:
        raise ValueError(f"Missing required fields: {missing}")
