import os
from dataclasses import dataclass
from typing import Dict

import yaml


class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid."""

    pass


@dataclass
class BridgeConfig:
    glueup_base_url: str
    glueup_public_key: str
    glueup_private_key: str
    glueup_email: str
    glueup_passphrase: str
    glueup_organization_id: str
    circle_base_url: str
    circle_api_token: str
    endpoints: Dict[str, Dict[str, str]]
    mapping: Dict


def load_config() -> BridgeConfig:
    """Load and validate application configuration from environment and YAML files.

    Returns:
        A validated BridgeConfig instance.

    Raises:
        ConfigurationError: If required environment variables are missing.
        FileNotFoundError: If YAML configuration files are not found.
        yaml.YAMLError: If YAML files contain invalid syntax.
    """
    # Load required environment variables
    required_env = {
        "GLUEUP_BASE_URL": os.getenv("GLUEUP_BASE_URL", "").strip(),
        "GLUEUP_PUBLIC_KEY": os.getenv("GLUEUP_PUBLIC_KEY", "").strip(),
        "GLUEUP_PRIVATE_KEY": os.getenv("GLUEUP_PRIVATE_KEY", "").strip(),
        "GLUEUP_EMAIL": os.getenv("GLUEUP_EMAIL", "").strip(),
        "GLUEUP_PASSPHRASE": os.getenv("GLUEUP_PASSPHRASE", "").strip(),
        "GLUEUP_ORGANIZATION_ID": os.getenv("GLUEUP_ORGANIZATION_ID", "").strip(),
        "CIRCLE_API_TOKEN": os.getenv("CIRCLE_API_TOKEN", "").strip(),
    }

    # Validate required variables are present
    missing = [key for key, value in required_env.items() if not value]
    if missing:
        raise ConfigurationError(
            f"Missing required environment variables: {', '.join(sorted(missing))}"
        )

    # Load optional environment variable with default
    circle_base_url = os.getenv(
        "CIRCLE_BASE_URL", "https://app.circle.so/api/admin/v2"
    ).strip()

    # Load YAML configuration files
    config_dir = os.path.dirname(__file__)

    with open(os.path.join(config_dir, "endpoints.yaml"), "r") as f:
        endpoints = yaml.safe_load(f)

    with open(os.path.join(config_dir, "mapping.yaml"), "r") as f:
        mapping = yaml.safe_load(f)

    return BridgeConfig(
        glueup_base_url=required_env["GLUEUP_BASE_URL"],
        glueup_public_key=required_env["GLUEUP_PUBLIC_KEY"],
        glueup_private_key=required_env["GLUEUP_PRIVATE_KEY"],
        glueup_email=required_env["GLUEUP_EMAIL"],
        glueup_passphrase=required_env["GLUEUP_PASSPHRASE"],
        glueup_organization_id=required_env["GLUEUP_ORGANIZATION_ID"],
        circle_base_url=circle_base_url,
        circle_api_token=required_env["CIRCLE_API_TOKEN"],
        endpoints=endpoints,
        mapping=mapping,
    )
