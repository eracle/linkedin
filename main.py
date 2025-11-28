# main.py
import asyncio
import logging

from linkedin.campaign_launcher import launch_campaign

logging.getLogger().handlers.clear()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(message)s",
    datefmt="%H:%M:%S",
)

asyncio.run(launch_campaign())
