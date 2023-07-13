"""This module contains the ``SeleniumMiddleware`` scrapy middleware"""

import logging

from scrapy import signals
from scrapy.http import HtmlResponse
from selenium import webdriver
from selenium.common import TimeoutException, StaleElementReferenceException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from conf import EMAIL, PASSWORD

logger = logging.getLogger(__name__)

"""
number of seconds used to wait the web page's loading.
"""
WAIT_TIMEOUT = 10


class SeleniumMiddleware:
    """Scrapy middleware handling the requests using selenium"""

    def __init__(self):
        SELENIUM_HOSTNAME = 'selenium'
        selenium_url = f'http://{SELENIUM_HOSTNAME}:4444/wd/hub'

        chrome_options = webdriver.ChromeOptions()
        self.driver = webdriver.Remote(
            command_executor=selenium_url,
            options=chrome_options
        )
        selenium_login(self.driver)
        # self.cookies = self.driver.get_cookie()
        # logger.debug(f"Cookies: {self.cookies}")
        # add_cookies_to_selenium(self.cookies, self.driver)

    @classmethod
    def from_crawler(cls, crawler):
        """Initialize the middleware with the crawler settings"""
        instance = cls()
        crawler.signals.connect(instance.spider_closed, signals.spider_closed)
        return instance

    def process_request(self, request, spider):
        """Process a request using the selenium driver if applicable"""
        self.driver.get(request.url)

        for cookie_name, cookie_value in request.cookies.items():
            self.driver.add_cookie(
                {
                    'name': cookie_name,
                    'value': cookie_value
                }
            )

        spider.wait_page_completion(self.driver)
        body = str.encode(self.driver.page_source)

        # Expose the driver via the "meta" attribute
        request.meta.update({'driver': self.driver})

        return HtmlResponse(
            self.driver.current_url,
            body=body,
            encoding='utf-8',
            request=request
        )

    def spider_closed(self):
        """Shutdown the driver when spider is closed"""
        self.driver.quit()


def selenium_login(driver):
    """
    Logs in in Linkedin.
    :param driver: The yet open selenium webdriver.
    :return: Nothing
    """
    driver.get(LINKEDIN_LOGIN_URL)

    logger.debug('Searching for the Login btn')
    get_by_xpath(driver, '//*[@id="username"]').send_keys(EMAIL)

    logger.debug('Searching for the password btn')
    get_by_xpath(driver, '//*[@id="password"]').send_keys(PASSWORD)

    logger.debug('Searching for the submit')
    get_by_xpath(driver, '//*[@type="submit"]').click()


LINKEDIN_LOGIN_URL = 'https://www.linkedin.com/login'


def get_by_xpath(driver, xpath, wait_timeout=None):
    """
    Get a web element through the xpath passed by performing a Wait on it.
    :param driver: Selenium web driver to use.
    :param xpath: xpath to use.
    :param wait_timeout: optional amounts of seconds before TimeoutException is raised, default WAIT_TIMEOUT is used otherwise.
    :return: The web element.
    """
    if wait_timeout is None:
        wait_timeout = WAIT_TIMEOUT
    return WebDriverWait(driver, wait_timeout).until(
        ec.presence_of_element_located(
            (By.XPATH, xpath)
        ))


def get_by_xpath_or_none(driver, xpath, wait_timeout=None, log=False):
    """
    Get a web element through the xpath string passed.
    If a TimeoutException is raised the else_case is called and None is returned.
    :param driver: Selenium Webdriver to use.
    :param xpath: String containing the xpath.
    :param wait_timeout: optional amounts of seconds before TimeoutException is raised, default WAIT_TIMEOUT is used otherwise.
    :return: The web element or None if nothing found.
    """
    try:
        return get_by_xpath(driver, xpath, wait_timeout=wait_timeout)
    except (TimeoutException, StaleElementReferenceException) as e:
        logger.info(
            f"Current URL:\n{driver.current_url}\nTimeoutException:\nXPATH: {xpath}\nError:{e}") if log else None
    except WebDriverException as e:
        logger.warning(f"Current URL:\n{driver.current_url}\nWebDriverException:\nXPATH: {xpath}\nError:{e}")


def add_cookies_to_selenium(cookies, driver):
    if cookies is not None:
        try:
            _ = driver.current_url
        except WebDriverException:
            driver.get("https://www.linkedin.com/404error")

        for cookie in cookies:
            if 'expiry' in cookie:
                del cookie['expiry']
            driver.add_cookie(cookie)
