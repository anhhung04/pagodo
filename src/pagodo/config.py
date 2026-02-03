import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional

CONFIG_PATH = Path.home() / ".config" / "pagodo.yml"

def load_config(config_path: Path = CONFIG_PATH) -> Dict[str, Any]:
    """
    Load configuration from a YAML file.
    Returns a dictionary with configuration values.
    """
    if not config_path.exists():
        return {}

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
            return config if config else {}
    except Exception as e:
        print(f"Warning: Failed to load config file at {config_path}: {e}")
        return {}

    return config.get(key, default)

def ensure_config_exists(config_path: Path = CONFIG_PATH) -> bool:
    """
    Ensure the configuration file exists. If not, create it with default values.
    Returns True if created, False if already existed.
    """
    if config_path.exists():
        return False

    default_dorks_dir = Path.home() / ".local" / "share" / "pagodo" / "dorks"
    
    default_config = {
        "dorks_dir": str(default_dorks_dir),
        "google_dorks_file": str(default_dorks_dir / "all_google_dorks.txt"),
        "domain": "",
        "minimum_delay": 1,
        "maximum_delay": 2,
        "disable_ssl_verification": False,
        "max_urls": 100,
        "verbosity": 4,
        "country_code": "vn",
        "engine": "serper",
        "max_results_per_search": 100,
        "serper_api_key": "",
        "serpapi_api_key": ""
    }

    try:
        if not config_path.parent.exists():
            config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, "w") as f:
            yaml.safe_dump(default_config, f, default_flow_style=False)
        return True
    except Exception as e:
        print(f"Warning: Failed to create default config file at {config_path}: {e}")
        return False
