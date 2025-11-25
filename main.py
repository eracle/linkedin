from linkedin.workflow import start_or_resume_campaign

scheduler = start_or_resume_campaign(
    handle="eracle",
    campaign_name="linked_in_connect_follow_up",
    input_csv="./assets/inputs/urls.csv"
)

try:
    scheduler.wait()  # or pause()
except KeyboardInterrupt:
    scheduler.shutdown()