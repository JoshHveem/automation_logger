from __future__ import annotations

import json
import os
from typing import Any, Dict


def load_automation_config(config_path: str = "automation.config") -> Dict[str, Any]:
    """
    Load JSON config. If file doesn't exist, returns {}.
    Expected JSON keys: automation_id (int), schema_name, table_name, path_mode
    """
    if not os.path.exists(config_path):
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)
