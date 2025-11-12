import random
import time  # For random delays
from datetime import datetime, timedelta

import yaml
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler

# Load YAML config
try:
    with open('../campaigns/example_campaign.yaml', 'r') as f:
        config = yaml.safe_load(f)
    # Reassign to the nested 'campaign' dict for simpler access
    config = config.get('campaign', {})
except FileNotFoundError:
    print("Error: YAML config file not found.")
    exit(1)
except yaml.YAMLError as e:
    print(f"Error parsing YAML: {e}")
    exit(1)

if not config:
    print("Error: Invalid or empty campaign configuration.")
    exit(1)

# Example action functions (stubbed; implement based on your tools)
def read_urls(profile_id, csv_file, url_column):
    # Logic to read URL from CSV for a specific profile_id
    print(f"Reading URL for profile {profile_id}")
    return {'url': 'https://linkedin.com/in/example'}  # Return data for next steps

def get_profile_info(profile_data):
    # Use linkedin_api to fetch info
    print(f"Fetching profile info for {profile_data['url']}")
    profile_data['full_name'] = 'John Doe'  # Mock
    # Write to output CSV as per config
    return profile_data

def connect(profile_data, note_template):
    # Use playwright to emulate human search and connect
    print(f"Sending connect request to {profile_data['full_name']}")
    # Check if connect succeeds or is pending; return status
    status = 'pending'  # Mock; in reality, detect via API or page inspection
    return status

def send_message(profile_data, template_file, template_type, ai_model):
    # Generate and send message
    print(f"Sending message to {profile_data['full_name']}")

def process_profile(profile_id):
    try:
        # Load or fetch profile data (e.g., from persisted storage or CSV)
        profile_data = read_urls(profile_id, config['actions'][0]['csv_file'], config['actions'][0]['url_column'])
        profile_data = get_profile_info(profile_data)

        # Apply random delay from config
        time.sleep(random.randint(config['settings']['limits']['delay_min'], config['settings']['limits']['delay_max']))

        connect_status = connect(profile_data, config['actions'][2].get('note_template'))

        if connect_status == 'pending':
            # Reschedule a check job for this profile in, say, 1 day
            check_time = datetime.now() + timedelta(days=1)
            scheduler.add_job(check_connection_and_message, 'date', run_date=check_time,
                              kwargs={'profile_id': profile_id, 'profile_data': profile_data},
                              id=f'check_{profile_id}')  # Unique ID for easy rescheduling
            print(f"Rescheduled check for profile {profile_id} in 1 day")
        elif connect_status == 'accepted':
            send_message(profile_data, config['actions'][3]['template_file'],
                         config['actions'][3]['template_type'], config['actions'][3]['ai_model'])
        else:
            # Handle failure, log, etc.
            pass
    except KeyError as e:
        print(f"Configuration error for profile {profile_id}: Missing key {e}")
    except Exception as e:
        print(f"Unexpected error for profile {profile_id}: {e}")

def check_connection_and_message(profile_id, profile_data):
    # Re-check connection status (e.g., via API)
    status = 'accepted'  # Mock check
    if status == 'accepted':
        send_message(profile_data, config['actions'][3]['template_file'],
                     config['actions'][3]['template_type'], config['actions'][3]['ai_model'])
    else:
        # Still pending? Reschedule again or give up after X attempts
        scheduler.reschedule_job(f'check_{profile_id}',
                                 trigger='date',
                                 run_date=datetime.now() + timedelta(days=1))
        print(f"Still pending; rescheduled check for {profile_id}")

# Configure job store for persistence
jobstores = {
    'default': SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')  # Persists to jobs.sqlite file
}
executors = {
    'default': ThreadPoolExecutor(20)  # Adjust for concurrency (e.g., to enforce daily limits)
}

scheduler = BackgroundScheduler(jobstores=jobstores, executors=executors)
scheduler.start()

# Example: Queue initial jobs for all profiles (e.g., from CSV)
# Assume you have a list of profile_ids from the input CSV
profile_ids = [1, 2, 3]  # Extract from CSV
for pid in profile_ids:
    scheduler.add_job(process_profile,
                      trigger='date',
                      run_date=datetime.now() + timedelta(seconds=5),
                      kwargs={'profile_id': pid},
                      id=f'process_{pid}')

# To enforce global limits (e.g., daily connections), track via a shared counter or DB
# and pause/reschedule if limits hit.

# Keep the script running to process jobs
try:
    while True:
        time.sleep(1)  # Or use signals for shutdown
except (KeyboardInterrupt, SystemExit):
    scheduler.shutdown()