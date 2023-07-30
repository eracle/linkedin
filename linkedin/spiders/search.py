import logging

from scrapy import Request, Spider

from linkedin.integrations.linkedin_api import extract_profile_from_url
from linkedin.integrations.selenium import get_by_xpath_or_none
from linkedin.middlewares.selenium import SeleniumSpiderMixin

logger = logging.getLogger(__name__)


def increment_index_at_end_url(response):
    # incrementing the index at the end of the url
    url = response.request.url
    next_url_split = url.split("=")
    index = int(next_url_split[-1])
    next_url = "=".join(next_url_split[:-1]) + "=" + str(index + 1)
    return index, next_url


class SearchSpider(Spider, SeleniumSpiderMixin):
    """
    Abstract class for generic search on linkedin.
    """

    allowed_domains = ("linkedin.com",)

    def __init__(self, name=None, **kwargs):
        super().__init__(name, **kwargs)
        self.user_profile = None
        self.profile_counter = 0

    def wait_page_completion(self, driver):
        """
        Abstract function, used to customize how the specific spider must wait for a search page completion.
        """
        get_by_xpath_or_none(driver, "//*[@id='global-nav']/div", wait_timeout=5)

    def send_connection_request(self, driver, user_profile_url):
        return
        # todo: continue from here
        # Navigate to the user's profile
        driver.get(user_profile_url)

        # Click the "Connect" button
        connect_button = driver.find_element_by_xpath("//button[text()='Connect']")
        connect_button.click()

        # Click the "Add a note" button
        add_note_button = driver.find_element_by_xpath("//button[text()='Add a note']")
        add_note_button.click()

        # Write the message in the textarea
        message_textarea = driver.find_element_by_xpath("//textarea[@name='message']")
        message_textarea.send_keys("Your personalized message here")

        # Click the "Send" button
        send_button = driver.find_element_by_xpath("//button[text()='Send']")
        send_button.click()

    def parse_search_list(self, response):
        continue_scrape = True
        driver = self.get_driver_from_response(response)
        if self.check_if_no_results_found(driver):
            logger.warning("No results found. Stopping crawl.")
            return

        for user_profile_url in self.iterate_users(driver):
            self.user_profile = extract_profile_from_url(user_profile_url, driver.get_cookies())
            if self.should_stop(response):
                continue_scrape = False
                break

            yield self.user_profile
            self.profile_counter += 1

            if self.should_send_connection_request():
                self.send_connection_request(driver, user_profile_url)

        if continue_scrape:
            next_url = self.get_next_url(response)
            yield self.create_next_request(next_url, response)

    def get_driver_from_response(self, response):
        return response.meta.pop("driver")

    def check_if_no_results_found(self, driver):
        no_result_found_xpath = "//div[contains(@class, 'search-reusable-search-no-results')]"
        return get_by_xpath_or_none(driver=driver, xpath=no_result_found_xpath, wait_timeout=3) is not None

    def role_filter(self):
        current_roles = [
            experience['title']
            for experience in self.user_profile['experience']
            if 'timePeriod' in experience and 'endDate' not in experience['timePeriod']
        ]
        return any(role in self.settings.get('ROLES_FOR_CONNECTION_REQUESTS') for role in current_roles)

    def should_send_connection_request(self):
        return self.settings.getbool('SEND_CONNECTION_REQUESTS') and self.role_filter()

    def get_next_url(self, response):
        index, next_url = increment_index_at_end_url(response)
        return next_url

    def create_next_request(self, next_url, response):
        return Request(url=next_url, priority=-1, callback=self.parse_search_list, meta=response.meta)

    def iterate_users(self, driver):
        for i in range(1, 11):
            self.sleep()
            container_xpath = f"//li[contains(@class, 'result-container')][{i}]"
            last_result = get_by_xpath_or_none(driver, container_xpath)
            if last_result:
                logger.debug(f"loading {i}th user")
                driver.execute_script("arguments[0].scrollIntoView();", last_result)
                # Use this XPath to select the <a> element
                link_elem = get_by_xpath_or_none(
                    last_result,
                    ".//a[contains(@class, 'app-aware-link') and contains(@href, '/in/')]",
                )
                if link_elem:
                    # Then extract the href attribute
                    user_url = link_elem.get_attribute("href")
                    logger.debug(f"Found user link:{user_url}")
                    yield user_url

    def should_stop(self, response):
        max_num_profiles = self.profile_counter >= self.settings.getint('MAX_PROFILES_TO_SCRAPE')
        if max_num_profiles:
            logger.info("Stopping Reached maximum number of profiles to scrape. Stopping crawl.")
        return max_num_profiles
