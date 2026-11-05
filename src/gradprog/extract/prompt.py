"""Versioned prompt, schema and settings under config/extraction (08 §1)."""

import json
from pathlib import Path

import yaml

PROMPT_VERSION = 1
SCHEMA_VERSION = 1
EXTRACT_RULES_VERSION = 1   # 08 §11: bumping it replays stored outputs without calling the LLM
PROMPT_SHA256 = {1: "fbbd0ab8f20f3b2776245718212064966dea3e20e51bcd0bbdf8876d646b8957"}
SCHEMA_SHA256 = {1: "e2edfadb4cec8555631868ec6ebef615f118a31ae35b9cf503d94ca625e5fd14"}
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
