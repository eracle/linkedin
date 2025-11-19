import random
import time

from linkedin.actions.login import PlaywrightResources


def wait(
        resources: PlaywrightResources,
        min_sleep: float = 1,
        max_sleep: float = 3,
):
    """Introduces a random sleep to simulate human-like behavior and avoid detection, after waiting for page load."""
    time.sleep(random.uniform(min_sleep, max_sleep))
    resources.page.wait_for_load_state("load")
