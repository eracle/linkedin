# linkedin/campaigns.py
"""
Campaign loader for the new 2025 singleton-based engine.

Key changes from old version:
  • handler is now a string → method name on LinkedInAutomation class
  • No function importing or pickling
  • parse_duration kept only for condition steps
  • Cleaner, smaller, safer
"""

import logging
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Dict, Optional, Literal

import yaml
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


# ==============================================================
# Config models (only validation – no runtime logic)
# ==============================================================

class StepConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["scrape", "action", "condition"]
    name: Optional[str] = None
    handler: str                                 # ← Just the method name, e.g. "send_connection_request"
    config: dict = {}


class CampaignConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campaign_name: str
    steps: list[StepConfig]
    settings: Optional[dict] = None


# ==============================================================
# Runtime Step & Campaign (lightweight – no callable!)
# ==============================================================

def parse_duration(s: str) -> timedelta:
    """Convert '14d', '6h', '30m' → timedelta"""
    s = s.strip().lower()
    num = int("".join(filter(str.isdigit, s or "0")) or "0")
    if s.endswith("d"): return timedelta(days=num)
    if s.endswith("h"): return timedelta(hours=num)
    if s.endswith("m"): return timedelta(minutes=num)
    if s.endswith("s"): return timedelta(seconds=num)
    raise ValueError(f"Invalid duration: {s}")


@dataclass
class Step:
    num: int
    type: str
    name: str
    handler: str                    # ← method name as string
    config: dict
    timeout: Optional[timedelta] = None
    check_interval: Optional[timedelta] = None


@dataclass
class Campaign:
    name: str
    steps: list[Step]
    settings: dict
    path: Path

    def __repr__(self):
        return f"<Campaign '{self.name}' [{len(self.steps)} steps]>"


# ==============================================================
# Registry – Django-style, unchanged
# ==============================================================

class CampaignRegistry:
    _registry: Dict[str, Campaign] = {}

    def register(self, campaign: Campaign):
        key = campaign.name
        if key in self._registry:
            logger.warning(f"Campaign '{key}' already registered – overwriting")
        self._registry[key] = campaign
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


# Global registry
campaigns = CampaignRegistry()


# ==============================================================
# Auto-loader – runs at import time
# ==============================================================

def _load_all_campaigns():
    if campaigns.all():
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
                    handler=s.handler,           # ← string only – resolved at runtime in workflow.py
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
            logger.info(f"Loaded campaign: {config.campaign_name}")

        except Exception as e:
            logger.error(f"Failed to load {yaml_file.name}: {e}", exc_info=True)


# Load everything on import
_load_all_campaigns()


# ==============================================================
# Debug entrypoint
# ==============================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print("Registered campaigns:")
    for c in campaigns:
        print(f"  → {c.name}")
        print(f"     path: {c.path.relative_to(Path.cwd())}")
        for step in c.steps:
            print(f"       [{step.type:8}] {step.name} → {step.handler}")