import logging

from scrapy import Request

from linkedin.integrations.selenium import get_by_xpath_or_none
from linkedin.spiders.search import SearchSpider

logger = logging.getLogger(__name__)


def extracts_see_all_url(driver):
    """
    Retrieve from the Company front page the url of the page containing the list of its employees.
    :param driver: The already opened (and logged in) webdriver, already located to the company's front page.
    :return: String: The "See All" URL.
    """
    logger.debug('Searching for the "See all * employees on LinkedIn" btn')
    see_all_xpath = "//a[contains(@href, '/search/results/people/')]"
    see_all_elem = get_by_xpath_or_none(driver, see_all_xpath)
    if not see_all_elem:
        logger.debug('"See all * employees on LinkedIn" btn not found')
    logger.debug(f"See all found: {see_all_elem.text}")
    see_all_url = see_all_elem.get_attribute("href")
    logger.debug(f"Found the following URL: {see_all_url}")
    return see_all_url


class CompaniesSpider(SearchSpider):
    name = "companies"

    def start_requests(self):
        yield Request(self.start_url, priority=-2, callback=self.parse_company)

    def parse_company(self, response):
        driver = response.meta.pop("driver")
        url = extracts_see_all_url(driver) + f"&page=1"
        yield Request(url=url, priority=-1, callback=self.parse_search_list)
