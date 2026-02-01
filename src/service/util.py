from pathlib import Path
import json

def _load_config() -> dict:
    config_path = Path(__file__).resolve().parent.parent.parent / "config.json"
    with open(config_path) as f:
        return json.load(f)