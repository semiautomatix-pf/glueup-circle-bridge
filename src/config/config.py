from dataclasses import dataclass
from typing import Dict, List, Optional
import yaml, os

@dataclass
class BridgeConfig:
    glueup_base_url: str
    glueup_header_a: str
    glueup_token: str
    circle_base_url: str
    circle_api_token: str
    endpoints: Dict[str, Dict[str, str]]
    mapping: Dict

def load_config() -> BridgeConfig:
    # env
    glueup_base_url = os.getenv("GLUEUP_BASE_URL", "").strip()
    glueup_header_a = os.getenv("GLUEUP_HEADER_A", "").strip()
    glueup_token = os.getenv("GLUEUP_TOKEN", "").strip()
    circle_base_url = os.getenv("CIRCLE_BASE_URL", "https://app.circle.so/api/admin/v2").strip()
    circle_api_token = os.getenv("CIRCLE_API_TOKEN", "").strip()

    # yaml
    with open(os.path.join(os.path.dirname(__file__), "endpoints.yaml"), "r") as f:
        endpoints = yaml.safe_load(f)

    with open(os.path.join(os.path.dirname(__file__), "mapping.yaml"), "r") as f:
        mapping = yaml.safe_load(f)

    return BridgeConfig(
        glueup_base_url=glueup_base_url,
        glueup_header_a=glueup_header_a,
        glueup_token=glueup_token,
        circle_base_url=circle_base_url,
        circle_api_token=circle_api_token,
        endpoints=endpoints,
        mapping=mapping,
    )
