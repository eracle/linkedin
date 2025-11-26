# linkedin/campaigns.py
import logging
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Dict, Optional, Callable, Literal

import yaml
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


# ==============================================================
# Simple models
# ==============================================================

class StepConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["scrape", "action", "condition"]
    name: Optional[str] = None
    handler: str
    config: dict = {}


class CampaignConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    campaign_name: str
    steps: list[StepConfig]
    settings: Optional[dict] = None


# ==============================================================
# Executable Step
# ==============================================================

def import_callable(path: str) -> Callable:
    from importlib import import_module
    mod_name, func_name = path.rsplit(".", 1)
    return getattr(import_module(mod_name), func_name)


def parse_duration(s: str) -> timedelta:
    s = s.strip().lower()
    num = int("".join(filter(str.isdigit, s or "0")) or "0")
    if s.endswith("d"): return timedelta(days=num)
    if s.endswith("h"): return timedelta(hours=num)
    if s.endswith("m"): return timedelta(minutes=num)
    raise ValueError(f"Invalid duration: {s}")


@dataclass
class Step:
    num: int
    type: str
    name: str
    handler: Callable
    config: dict
    timeout: Optional[timedelta] = None
    check_interval: Optional[timedelta] = None

    def execute(self, context: dict, profile: Optional[dict] = None):
        context["params"] = self.config
        logger.info(f"[{context.get('campaign_name')}] Step {self.num} [{self.type.upper()}] {self.name}")
        if self.type == "scrape":
            return self.handler(context)
        return self.handler(context, profile)


@dataclass
class Campaign:
    name: str
    steps: list[Step]
    settings: dict
    path: Path

    def __repr__(self):
        return f"<Campaign '{self.name}' [{len(self.steps)} steps]>"


# ==============================================================
# Django-style Campaign Registry (the magic)
# ==============================================================

class CampaignRegistry:
    """
    Just like django.apps.apps – one global object with campaigns as attributes.
    """

    def __init__(self):
        self._registry: Dict[str, Campaign] = {}

    def register(self, campaign: Campaign):
        key = campaign.name
        if key in self._registry:
            logger.warning(f"Campaign '{key}' already registered – overwriting")
        self._registry[key] = campaign
        # Make it accessible as attribute: campaigns.my_campaign_name
        sanitized = key.replace("-", "_").replace(" ", "_")
        setattr(self, sanitized, campaign)

    def get(self, name: str) -> Optional[Campaign]:
        return self._registry.get(name)

    def all(self) -> list[Campaign]:
        return list(self._registry.values())

    def __getitem__(self, name: str) -> Campaign:
        return self._registry[name]

    def __contains__(self, name: str) -> bool:
        return name in self._registry

    def __iter__(self):
        return iter(self._registry.values())

    def __len__(self):
        return len(self._registry)


# Global registry – this is your "django.apps.apps"
campaigns = CampaignRegistry()


# ==============================================================
# Auto-loader – runs once at import time (like Django's AppConfig.ready)
# ==============================================================

def _load_all_campaigns():
    if campaigns.all():  # Already loaded
        return

    campaigns_dir = Path.cwd() / "assets" / "campaigns"
    if not campaigns_dir.is_dir():
        logger.warning(f"Campaigns directory not found: {campaigns_dir}")
        return

    for yaml_file in campaigns_dir.glob("*.y*ml"):
        try:
            raw = yaml.safe_load(yaml_file.read_text(encoding="utf-8")) or {}
            config = CampaignConfig.model_validate(raw)

            steps = []
            for i, s in enumerate(config.steps, 1):
                timeout = check_interval = None
                if s.type == "condition":
                    timeout = parse_duration(s.config.get("timeout", "14d"))
                    check_interval = parse_duration(s.config.get("check_interval", "6h"))

                step = Step(
                    num=i,
                    type=s.type,
                    name=s.name or f"{s.type}_{i}",
                    handler=import_callable(s.handler),
                    config=s.config.copy(),
                    timeout=timeout,
                    check_interval=check_interval,
                )
                steps.append(step)

            campaign = Campaign(
                name=config.campaign_name,
                steps=steps,
                settings=config.settings or {},
                path=yaml_file,
            )
            campaigns.register(campaign)
            logger.info(f"Registered campaign: {config.campaign_name}")

        except Exception as e:
            logger.error(f"Failed to load {yaml_file.name}: {e}")


# Auto-load on import (just like Django!)
_load_all_campaigns()

# ==============================================================
# Debug
# ==============================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print("All registered campaigns:")
    for c in campaigns:
        print(f"  → {c}")
        print(f"     access: campaigns.{c.name.replace('-', '_')}")
