import random
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Callable

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler

from . import campaign_parser, database, actions

# --- Global Instances ---
SCHEDULER: BackgroundScheduler = None

# Maps step types from campaign YAML to their corresponding action functions.
ACTION_MAP: Dict[str, Callable] = {
    'read_urls': actions.read_urls,
    'get_profile_info': actions.get_profile_info,
    'connect': actions.connect,
    'send_message': actions.send_message,
}

# Maps step types from campaign YAML to their corresponding condition check functions.
CONDITION_MAP: Dict[str, Callable] = {
    'wait_for_connection': actions.is_connection_accepted
}

# --- Workflow Functions ---

def start_workflow(linkedin_url: str, campaign: campaign_parser.Campaign):
    """Initiates the first step of a campaign for a given URL."""
    print(f"\nStarting workflow for URL '{linkedin_url}' with campaign '{campaign.campaign_name}'")
    execute_step(linkedin_url, campaign, 0)

def execute_step(linkedin_url: str, campaign: campaign_parser.Campaign, step_index: int):
    """Executes a single step of the campaign."""
    if step_index >= len(campaign.steps):
        print(f"Workflow for {linkedin_url} completed.")
        return

    step = campaign.steps[step_index]
    step_type = step.type

    if step_type in ACTION_MAP:
        action_func = ACTION_MAP[step_type]
        action_func(linkedin_url, step.model_dump())
        execute_step(linkedin_url, campaign, step_index + 1)

    elif step_type in CONDITION_MAP:
        print(f"Executing step: {step_type}")
        # Create a unique job ID for rescheduling
        job_id = f"check_{linkedin_url.replace('/', '_').replace(':', '')}_{step_index}"

        SCHEDULER.add_job(
            check_condition_and_proceed_job,
            trigger='date',
            run_date=datetime.now() + timedelta(seconds=5), # Check after 5 seconds initially
            kwargs={
                'linkedin_url': linkedin_url,
                'campaign': campaign,
                'step_index': step_index
            },
            id=job_id,
            replace_existing=True # Ensure only one job for this step/url exists
        )
    else:
        print(f"Warning: Unknown step type '{step_type}' for {linkedin_url}. Skipping.")
        execute_step(linkedin_url, campaign, step_index + 1)

def check_condition_and_proceed(linkedin_url: str, campaign: campaign_parser.Campaign, step_index: int):
    """The logic that periodically checks a condition."""
    step = campaign.steps[step_index]
    condition_func = CONDITION_MAP[step.type]

    if condition_func(linkedin_url):
        print(f"Condition '{step.type}' met for {linkedin_url}. Proceeding to next step.")
        execute_step(linkedin_url, campaign, step_index + 1)
    else:
        job_id = f"check_{linkedin_url.replace('/', '_').replace(':', '')}_{step_index}"
        job = SCHEDULER.get_job(job_id)

        # TODO: Implement robust timeout logic based on campaign settings
        # For now, just reschedule
        reschedule_time = datetime.now() + timedelta(seconds=15) # Reschedule after 15 seconds
        SCHEDULER.reschedule_job(job_id, trigger='date', run_date=reschedule_time)
        print(f"Rescheduled check for {linkedin_url} at {reschedule_time.isoformat()}")

# --- Scheduler Callback ---

def check_condition_and_proceed_job(linkedin_url: str, campaign: campaign_parser.Campaign, step_index: int):
    """Standalone function for APScheduler to call, avoiding serialization issues."""
    check_condition_and_proceed(linkedin_url, campaign, step_index)

# --- Main Execution ---

def main():
    """Main function to set up and run the scheduler and workflows."""
    global SCHEDULER

    print("Initializing database...")
    database.initialize_database()

    print("Initializing scheduler...")
    jobstores = {'default': SQLAlchemyJobStore(url='sqlite:///linkedin.db')}
    executors = {'default': ThreadPoolExecutor(5)}
    SCHEDULER = BackgroundScheduler(jobstores=jobstores, executors=executors)
    SCHEDULER.start()

    print("Loading campaigns...")
    try:
        campaigns = campaign_parser.load_campaigns()
        if not campaigns:
            print("No campaigns found. Exiting.")
            return
    except ValueError as e:
        print(f"Could not load campaigns: {e}")
        return

    campaign_to_run = campaigns[0]

    # For demonstration purposes, we're hardcoding a few URLs.
    # In a real scenario, these would be read from a CSV via the 'read_urls' campaign step.
    profile_urls = [
        "https://linkedin.com/in/johndoe",
        "https://linkedin.com/in/janedoe",
        "https://linkedin.com/in/peterjones"
    ]
    for url in profile_urls:
        start_workflow(url, campaign_to_run)

    print("\nScheduler is running. Press Ctrl+C to exit.")
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        print("Shutting down scheduler...")
        SCHEDULER.shutdown()
        print("Shutdown complete.")

if __name__ == "__main__":
    main()