# -*- coding: utf-8 -*-
import logging
from random import uniform
from time import sleep

from scrapy import Request, Spider

from linkedin.integrations.linkedin_api import extract_profile_id_from_url
from linkedin.integrations.selenium import get_by_xpath, get_by_xpath_or_none
from linkedin.spiders.search import increment_index_at_end_url

logger = logging.getLogger(__name__)

URLS_FILE = "data/urls.txt"


def extracts_see_all_url(driver):
    """
    Retrieve from the Company front page the url of the page containing the list of its employees.
    :param driver: The already opened (and logged in) webdriver, already located to the company's front page.
    :return: String: The "See All" URL.
    """
    logger.debug('Searching for the "See all * employees on LinkedIn" btn')
    see_all_xpath = "//a[contains(@href, '/search/results/people/')]"
    see_all_elem = get_by_xpath(driver, see_all_xpath)
    logger.debug(f'See all found: {see_all_elem.text}')
    see_all_url = see_all_elem.get_attribute('href')
    logger.debug(f'Found the following URL: {see_all_url}')
    return see_all_url


def extract_company(driver):
    """
    Extract company name from a search result page.
    :param driver: The selenium webdriver.
    :return: The company string, None if something wrong.
    """
    company_xpath = '//li[@class="search-s-facet search-s-facet--facetCurrentCompany inline-block ' \
                    'search-s-facet--is-closed ember-view"]/form/button/div/div/h3 '
    company_elem = get_by_xpath_or_none(driver, company_xpath)
    return company_elem.text if company_elem is not None else None


def parse_company(response):
    driver = response.meta.pop('driver')
    url = extracts_see_all_url(driver) + f'&page=1'
    yield Request(url=url, priority=-1, callback=parse_search_list)


def iterate_users(driver):
    for i in range(1, 11):

        container_xpath = f"//li[contains(@class, 'result-container')][{i}]"
        last_result = get_by_xpath_or_none(driver, container_xpath)
        if last_result:
            logger.debug(f'loading {i}th user')
            driver.execute_script("arguments[0].scrollIntoView();", last_result)
            # Use this XPath to select the <a> element
            link_elem = get_by_xpath_or_none(last_result,
                                             ".//a[contains(@class, 'app-aware-link') and contains(@href, '/in/')]")
            if link_elem:
                # Then extract the href attribute
                user_url = link_elem.get_attribute('href')
                logger.debug(f"Found user link:{user_url}")
                yield user_url

        sleep(0.4)


class CompaniesSpider(Spider):
    name = 'companies'
    allowed_domains = ('linkedin.com',)

    def start_requests(self):
        with open(URLS_FILE, "rt") as f:
            for url in [url.strip() for url in f]:
                yield Request(url, priority=-2, callback=self.parse_search_list)

    def parse_search_list(self, response):
        logger.debug("parse search list")
        driver = response.meta.pop('driver')
        no_result_found_xpath = "//div[contains(@class, 'search-reusable-search-no-results')]"
        no_result_response = get_by_xpath_or_none(driver=driver,
                                                  xpath=no_result_found_xpath,
                                                  wait_timeout=3)
        if no_result_response:
            # no results message shown: stop crawling this company
            logger.warning("no results message shown: stop crawling this company")
            return
        for user_profile_url in iterate_users(driver):
            sleep(2)
            yield extract_profile_id_from_url(user_profile_url, driver.get_cookies())

        index, next_url = increment_index_at_end_url(response)

        yield Request(url=next_url, priority=-1, callback=self.parse_search_list)

    def wait_page_completion(self, driver):
        """
        Abstract function, used to customize how the specific spider must wait for a search page completion.
        Blank by default
        :param driver:
        :return:
        """
        get_by_xpath_or_none(driver, "//*[@id='global-nav']/div", wait_timeout=5)

    def sleep(self):
        delay = self.settings.getint('DOWNLOAD_DELAY')
        randomize_delay = self.settings.getbool('RANDOMIZE_DOWNLOAD_DELAY')
        if delay:
            if randomize_delay:
                delay = uniform(0.5 * delay, 1.5 * delay)
            sleep(delay)
