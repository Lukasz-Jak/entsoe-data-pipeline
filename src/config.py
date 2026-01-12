import os
import yaml
import logging
from typing import Any, Dict
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    # Override with environment variables if necessary
    api_key = os.getenv("ENTSOE_API_KEY")
    
    if not api_key:
        msg = "Missing ENTSO-E API key. Please set the ENTSOE_API_KEY environment variable."
        logger.error(msg)
        raise ValueError(msg)
        
    config['api']['key'] = api_key
    
    return config
