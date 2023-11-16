import json
from typing import Any, Dict

def load_config(file_path: str) -> Dict[str, Any]:
    with open(file_path, "r") as file:
        return json.load(file)

# Load the configuration at the start of the application
CONFIG = load_config("./config.json")
