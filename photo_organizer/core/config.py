"""Configuration loader for photo organizer."""

from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from pydantic import BaseModel, Field


class PathsConfig(BaseModel):
    source: Path = Path("G:/photo_incoming")
    target: Path = Path("G:/Photos/정리됨")


class GroupingConfig(BaseModel):
    time_gap_hours: int = 18
    default_event_name: str = "event"


class DuplicateConfig(BaseModel):
    use_partial_hash: bool = True
    use_perceptual_hash: bool = False
    action: str = "move_to_duplicates"  # move_to_duplicates | delete | ask


class AutomationConfig(BaseModel):
    interval_minutes: int = 30
    dry_run: bool = False


class Config(BaseModel):
    paths: PathsConfig = Field(default_factory=PathsConfig)
    grouping: GroupingConfig = Field(default_factory=GroupingConfig)
    duplicate: DuplicateConfig = Field(default_factory=DuplicateConfig)
    automation: AutomationConfig = Field(default_factory=AutomationConfig)
    device_alias: Dict[str, str] = Field(default_factory=dict)


def load_config(config_path: Optional[Path] = None) -> Config:
    """
    Load configuration from YAML file.
    If file doesn't exist or fails to load, return default config.
    """
    if config_path is None:
        # Try default locations
        candidates = [
            Path("config.yaml"),
            Path(__file__).parent.parent / "config.yaml",
            Path.cwd() / "config.yaml",
        ]
        for c in candidates:
            if c.exists():
                config_path = c
                break

    if config_path is None or not config_path.exists():
        print("[WARN] config.yaml not found. Using default settings.")
        return Config()

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        # Convert string paths to Path objects
        if "paths" in data:
            if "source" in data["paths"]:
                data["paths"]["source"] = Path(data["paths"]["source"])
            if "target" in data["paths"]:
                data["paths"]["target"] = Path(data["paths"]["target"])

        return Config(**data)
    except Exception as e:
        print(f"[WARN] Failed to load config.yaml: {e}. Using defaults.")
        return Config()


def save_config(config: Config, config_path: Path) -> None:
    """Save config to YAML file."""
    data = config.model_dump(mode="json")
    # Convert Path objects back to strings for YAML
    if "paths" in data:
        if isinstance(data["paths"].get("source"), Path):
            data["paths"]["source"] = str(data["paths"]["source"])
        if isinstance(data["paths"].get("target"), Path):
            data["paths"]["target"] = str(data["paths"]["target"])

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)