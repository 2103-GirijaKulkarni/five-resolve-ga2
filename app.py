import os
from typing import Optional

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow the grading page/browser to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def to_int(value):
    return int(value)


def to_bool(value):
    return str(value).strip().lower() in {"true", "1", "yes", "on"}


def coerce(key, value):
    if key in {"port", "workers"}:
        return to_int(value)

    if key == "debug":
        return to_bool(value)

    return str(value)


def build_config() -> dict:
    # 1. Lowest precedence: hardcoded defaults
    config = {
        "port": 8000,
        "workers": 1,
        "debug": False,
        "log_level": "info",
        "api_key": "default-secret-000",
    }

    # 2. Environment-specific YAML
    env_name = os.getenv("APP_ENV", "development")
    yaml_file = f"config.{env_name}.yaml"

    if os.path.exists(yaml_file):
        with open(yaml_file, "r") as f:
            yaml_config = yaml.safe_load(f) or {}

        for key, value in yaml_config.items():
            config[key] = value

    # 3. .env file
    env_file_values = dotenv_values(".env")

    for key, value in env_file_values.items():
        if key == "NUM_WORKERS":
            config["workers"] = value
        elif key.startswith("APP_"):
            config_key = key[len("APP_"):].lower()
            config[config_key] = value

    # 4. Highest file/env precedence: real OS environment variables
    for key, value in os.environ.items():
        if key.startswith("APP_"):
            config_key = key[len("APP_"):].lower()
            config[config_key] = value

    return config


@app.get("/effective-config")
def effective_config(
    set: Optional[list[str]] = Query(default=None)
):
    config = build_config()

    # 5. Highest precedence of all: CLI/query overrides
    if set:
        for item in set:
            if "=" not in item:
                continue

            key, value = item.split("=", 1)
            config[key] = value

    # Convert values to the required JSON types
    final_config = {
        key: coerce(key, value)
        for key, value in config.items()
    }

    # Never reveal the API key
    final_config["api_key"] = "****"

    return final_config
