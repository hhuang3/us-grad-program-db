"""Versioned prompt, schema and settings under config/extraction (08 §1)."""

import json
from pathlib import Path

import yaml

PROMPT_VERSION = 2
SCHEMA_VERSION = 1
EXTRACT_RULES_VERSION = 2   # 08 §11: bumping it replays stored outputs without calling the LLM
PROMPT_SHA256 = {1: "687420e5e66b214076b88e566fdfe09f23d8194ed07875bb5ddcee28bba3c2da",
                 2: "1380267939aef727aabd24519ec9fcfa4961f479f4b439eb4159f4d911c2d6bd"}
SCHEMA_SHA256 = {1: "a977415d4477f12f56c48730b371cff81d1d12d2124504311b1afe91c2d7b947"}
CONFIG_DIR = Path(__file__).resolve().parents[3] / "config" / "extraction"
USER_FIELDS = ("program_name", "degree_type", "page_url", "page_type", "owner_level", "scope_note")


def prompt_files(version=PROMPT_VERSION, root=CONFIG_DIR):
    return [Path(root) / f"prompt_v{version}" / "system.md", Path(root) / f"prompt_v{version}" / "user.md"]


def schema_file(version=SCHEMA_VERSION, root=CONFIG_DIR):
    return Path(root) / f"schema_v{version}.json"


def load_schema(version=SCHEMA_VERSION, root=CONFIG_DIR):
    return json.loads(schema_file(version, root).read_text(encoding="utf-8"))


def load_settings(root=CONFIG_DIR):
    return yaml.safe_load((Path(root) / "extraction.yaml").read_text(encoding="utf-8"))


def build_prompt(values, body, version=PROMPT_VERSION, root=CONFIG_DIR):
    """(system, user). The page text goes in last so nothing inside it is treated as a placeholder (08 §4.1)."""
    system, user = (p.read_text(encoding="utf-8") for p in prompt_files(version, root))
    for name in USER_FIELDS:
        user = user.replace("{{" + name + "}}", values[name] or "(none)")
    return system, user.replace("{{page_text}}", body)
