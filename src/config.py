import os
import yaml
from typing import Any, Dict
from dotenv import load_dotenv

load_dotenv()

def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    # Override with environment variables if necessary
    config['api']['key'] = os.getenv("ENTSOE_API_KEY")
    
    return config
