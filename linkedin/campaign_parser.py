import os
import yaml
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ValidationError, ConfigDict

# --- Pydantic Models for Validation ---

class Step(BaseModel):
    """A single step in a campaign workflow."""
    action: str = Field(..., min_length=1)
    step_type: str = "action"
    # Allow any other parameters for flexibility
    model_config = ConfigDict(extra='allow')

class Campaign(BaseModel):
    """A campaign workflow."""
    campaign_name: str = Field(..., min_length=1)
    steps: List[Step] = Field(..., min_length=1)

# --- Campaign Loader ---

def load_campaigns(campaigns_dir: Optional[str] = None) -> List[Campaign]:
    """
    Loads all YAML campaign files from a directory, parses them, and validates their structure using Pydantic.

    Args:
        campaigns_dir: The path to the directory containing campaign YAML files.
                       If None, defaults to 'assets/campaigns' relative to the project root.

    Returns:
        A list of validated Campaign objects.

    Raises:
        ValueError: If a campaign file is invalid or the directory is not found.
    """
    if campaigns_dir is None:
        # Assumes script is run from the project root
        campaigns_dir = os.path.join(os.getcwd(), "assets", "campaigns")

    if not os.path.isdir(campaigns_dir):
        raise ValueError(f"Campaign directory not found at: {campaigns_dir}")

    campaigns = []
    for filename in os.listdir(campaigns_dir):
        if not filename.endswith((".yaml", ".yml")):
            continue

        filepath = os.path.join(campaigns_dir, filename)
        try:
            with open(filepath, 'r') as f:
                data = yaml.safe_load(f)
            
            if not isinstance(data, dict):
                 raise ValueError("root should be a dictionary")

            campaign = Campaign.model_validate(data)
            campaigns.append(campaign)

        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML in {filename}: {e}")
        except ValidationError as e:
            raise ValueError(f"Invalid campaign structure in {filename}:\n{e}")
        except ValueError as e:
            raise ValueError(f"Invalid campaign file format in {filename}: {e}")


    return campaigns

if __name__ == "__main__":
    print("Attempting to load and validate all campaigns...")
    try:
        loaded_campaigns = load_campaigns()
        print(f"Successfully loaded and validated {len(loaded_campaigns)} campaign(s):")
        for campaign in loaded_campaigns:
            print(f"- Campaign: '{campaign.campaign_name}' with {len(campaign.steps)} steps.")
    except ValueError as e:
        print(f"Error: {e}")
