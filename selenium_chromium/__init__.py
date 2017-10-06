import logging
import os

from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


_ROOT = os.path.abspath(os.path.dirname(__file__))


def get_chromium_browser_path(path):
    return os.path.join(_ROOT, 'chromium-browser', path)


def init_chromium(headless=True):

    chrome_options = Options()
    chrome_options.add_argument('--disable-notifications')
    c_path = get_chromium_browser_path('chromium-browser')
    logger.info('Chromium path: %s' % c_path)
    chrome_options.binary_location = c_path

    if headless:
        chrome_options.add_argument('--headless')

    # --remote-debugging-port=9222 https://chromium.org

    prefs = {"credentials_enable_service": False, "profile.password_manager_enabled": False}
    chrome_options.add_experimental_option("prefs", prefs)
    driver_path = get_chromium_browser_path(os.path.join('driver', 'chromedriver'))
    logger.info('Driver path: %s' % driver_path)
    logger.info('Init Chromium - headless: %s' % headless)
    webdriver = WebDriver(executable_path=driver_path, chrome_options=chrome_options)
    return webdriver
