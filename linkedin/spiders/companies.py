# -*- coding: utf-8 -*-
import copy

from scrapy import Request

from linkedin.spiders.search import SearchSpider
from linkedin.spiders.selenium import get_by_xpath_or_none, get_by_xpath, init_chromium, login

URLS_FILE = "urls.txt"

"""
Placeholder used to recognize the 'See all 27,569 employees on LinkedIn' clickable button,
in the 'https://www.linkedin.com/company/*/' style pages.
"""
SEE_ALL_PLACEHOLDER = 'See all'


class CompaniesSpider(SearchSpider):
    name = 'companies'
    allowed_domains = ['www.linkedin.com']

    with open(URLS_FILE, "rt") as f:
        start_urls = [url.strip() for url in f]

    def parse(self, response):
        driver = response.meta.pop('driver')
        url = extracts_see_all_url(driver) + f'&page=1'
        driver.close()
        return Request(url=url,
                       callback=super().parser_search_results_page,
                       dont_filter=True,
                       meta=copy.deepcopy(response.meta),
                       )


######################
# Module's functions:
######################

def extracts_see_all_url(driver):
    """
    Retrieve from the the Company front page the url of the page containing the list of its employees.
    :param driver: The already opened (and logged in) webdriver, already located to the company's front page.
    :return: String: The "See All" URL.
    """
    print('Searching for the "See all * employees on LinkedIn" btn')
    see_all_xpath = f'//*[starts-with(text(),"{SEE_ALL_PLACEHOLDER}")]'
    see_all_elem = get_by_xpath(driver, see_all_xpath)
    see_all_ex_text = see_all_elem.text

    a_elem = driver.find_element_by_link_text(see_all_ex_text)
    see_all_url = a_elem.get_attribute('href')
    print(f'Found the following URL: {see_all_url}')
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
