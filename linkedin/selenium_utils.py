from selenium import webdriver
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

"""
number of seconds used to wait the web page's loading.
"""
WAIT_TIMEOUT = 10


def get_by_xpath(driver, xpath):
    """
    Get a web element through the xpath passed by performing a Wait on it.
    :param driver: Selenium web driver to use.
    :param xpath: xpath to use.
    :return: The web element
    """
    return WebDriverWait(driver, WAIT_TIMEOUT).until(
        ec.presence_of_element_located(
            (By.XPATH, xpath)
        ))


def init_chromium(selenium_host):
    selenium_url = 'http://%s:4444/wd/hub' % selenium_host

    print('Initializing chromium, remote url: %s' % selenium_url)

    chrome_options = DesiredCapabilities.CHROME
    # chrome_options.add_argument('--disable-notifications')

    prefs = {"credentials_enable_service": False, "profile.password_manager_enabled": False}

    chrome_options['prefs'] = prefs

    driver = webdriver.Remote(command_executor=selenium_url,
                              desired_capabilities=chrome_options)
    return driver