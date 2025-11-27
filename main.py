# main.py
import time

from linkedin.workflow import start_or_resume_campaign

engine = start_or_resume_campaign(
    handle="eracle",
    campaign_name="linked_in_connect_follow_up",
    input_csv="./assets/inputs/urls.csv"
)

print("Campaign running. Ctrl+C to stop.")
try:
    while True:
        time.sleep(60)
        print("Status →", engine.status())
except KeyboardInterrupt:
    print("\nStopping...")
    engine.stop()
