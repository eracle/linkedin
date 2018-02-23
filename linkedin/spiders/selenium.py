from selenium import webdriver
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from conf import EMAIL, PASSWORD

"""
number of seconds used to wait the web page's loading.
"""
WAIT_TIMEOUT = 10

LINKEDIN_LOGIN_URL = 'https://www.linkedin.com/'

""" Hostname used in the inter-comuication between docker instances,
from the scrapy controller to the selenium instance."""
SELENIUM_HOSTNAME = 'selenium'


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


class SeleniumSpiderMixin:
    def __init__(self, *a, **kw):
        self.driver = init_chromium(SELENIUM_HOSTNAME)

        # Stop web page from asking me if really want to leave - past implementation, FIREFOX
        # profile = webdriver.FirefoxProfile()
        # profile.set_preference('dom.disable_beforeunload', True)
        # self.driver = webdriver.Firefox(profile)

        self.driver.get(LINKEDIN_LOGIN_URL)

        print('Searching for the Login btn')
        get_by_xpath(self.driver, '//*[@class="login-email"]').send_keys(EMAIL)

        print('Searching for the password btn')
        get_by_xpath(self.driver, '//*[@class="login-password"]').send_keys(PASSWORD)

        print('Searching for the submit')
        get_by_xpath(self.driver, '//*[@id="login-submit"]').click()

        super().__init__(*a, **kw)
