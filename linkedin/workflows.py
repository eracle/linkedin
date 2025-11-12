import random
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Callable

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler

from . import campaign_parser

# --- Action Functions (Stubs) ---
# These functions contain the actual logic for interacting with LinkedIn.

def read_urls(state: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    print(f"Executing step: read_urls for profile {state.get('profile_id')}")
    # In a real implementation, you would read from params['csv_file']
    state['linkedin_url'] = 'https://linkedin.com/in/example'
    return state

def get_profile_info(state: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    print(f"Executing step: get_profile_info for {state['linkedin_url']}")
    state['full_name'] = 'John Doe'
    state['current_company'] = 'Acme Corp'
    return state

def connect(state: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    print(f"Executing step: connect with {state['full_name']}")
    # In a real implementation, this would return 'pending', 'accepted', or 'failed'
    state['connection_status'] = 'pending' 
    return state

def send_message(state: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    print(f"Executing step: send_message to {state['full_name']}")
    return state

# --- Condition Check Functions ---

def is_connection_accepted(state: Dict[str, Any]) -> bool:
    """Checks if a connection request was accepted."""
    print(f"Checking connection status for {state['full_name']}...")
    # In a real implementation, this would involve an API call or browser check.
    # To simulate, let's randomly accept it.
    is_accepted = random.choice([True, False])
    if is_accepted:
        print("Connection accepted!")
        state['connection_status'] = 'accepted'
        return True
    else:
        print("Connection still pending.")
        return False

# --- Workflow Engine ---

class WorkflowEngine:
    def __init__(self):
        self.action_map: Dict[str, Callable] = {
            'read_urls': read_urls,
            'get_profile_info': get_profile_info,
            'connect': connect,
            'send_message': send_message,
        }
        self.condition_map: Dict[str, Callable] = {
            'wait_for_connection': is_connection_accepted
        }

    def start_workflow(self, profile_id: Any, campaign: campaign_parser.Campaign):
        """Initiates the first step of a campaign for a given profile."""
        print(f"\nStarting workflow for profile '{profile_id}' with campaign '{campaign.campaign_name}'")
        initial_state = {'profile_id': profile_id}
        self._execute_step(initial_state, campaign, 0)

    def _execute_step(self, state: Dict[str, Any], campaign: campaign_parser.Campaign, step_index: int):
        """Executes a single step of the campaign."""
        if step_index >= len(campaign.steps):
            print(f"Workflow for profile {state['profile_id']} completed.")
            return

        step = campaign.steps[step_index]
        step_type = step.type
        
        if step_type in self.action_map:
            action_func = self.action_map[step_type]
            updated_state = action_func(state, step.model_dump())
            self._execute_step(updated_state, campaign, step_index + 1)

        elif step_type in self.condition_map:
            print(f"Executing step: {step_type}")
            job_id = f"check_{state['profile_id']}_{step_index}"
            
            SCHEDULER.add_job(
                check_condition_and_proceed_job,
                trigger='date',
                run_date=datetime.now() + timedelta(seconds=5),
                kwargs={
                    'state': state,
                    'campaign': campaign,
                    'step_index': step_index
                },
                id=job_id
            )
        else:
            print(f"Warning: Unknown step type '{step_type}' for profile {state['profile_id']}. Skipping.")
            self._execute_step(state, campaign, step_index + 1)

    def _check_condition_and_proceed(self, state: Dict[str, Any], campaign: campaign_parser.Campaign, step_index: int):
        """The logic that periodically checks a condition."""
        step = campaign.steps[step_index]
        condition_func = self.condition_map[step.type]

        if condition_func(state):
            self._execute_step(state, campaign, step_index + 1)
        else:
            job_id = f"check_{state['profile_id']}_{step_index}"
            job = SCHEDULER.get_job(job_id)
            
            if job and job.next_run_time > datetime.now() + timedelta(days=1):
                 print(f"Timeout reached for step '{step.type}' on profile {state['profile_id']}. Workflow stopping.")
                 SCHEDULER.remove_job(job.id)
                 return

            reschedule_time = datetime.now() + timedelta(seconds=15)
            SCHEDULER.reschedule_job(job_id, trigger='date', run_date=reschedule_time)
            print(f"Rescheduled check for profile {state['profile_id']} at {reschedule_time.isoformat()}")

# --- Global Instances and Scheduler Callback ---

SCHEDULER: BackgroundScheduler = None
ENGINE: WorkflowEngine = None

def check_condition_and_proceed_job(state: Dict[str, Any], campaign: campaign_parser.Campaign, step_index: int):
    """Standalone function for APScheduler to call, avoiding serialization issues."""
    ENGINE._check_condition_and_proceed(state, campaign, step_index)


def main():
    """Main function to set up and run the scheduler and workflows."""
    global SCHEDULER, ENGINE
    
    print("Initializing scheduler...")
    jobstores = {'default': SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')}
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

    ENGINE = WorkflowEngine()
    campaign_to_run = campaigns[0]

    profile_ids = [1, 2, 3]
    for pid in profile_ids:
        ENGINE.start_workflow(pid, campaign_to_run)

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