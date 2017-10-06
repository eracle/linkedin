import scrapy
from selenium.webdriver.common.keys import Keys

from selenium_chromium import init_chromium

from conf import EMAIL, PASSWORD
from selenium_utils import get_by_xpath


LINKEDIN_URL = 'https://it.linkedin.com/'


class Linkedin(scrapy.Spider):
    name = "linkedin"
    start_urls = [
        'https://it.linkedin.com/in/antonio-ercole-de-luca-1973401b'
    ]

    def __init__(self):
        self.driver = init_chromium(False)

        # Stop web page from asking me if really want to leave - past implementation, FIREFOX
        # profile = webdriver.FirefoxProfile()
        # profile.set_preference('dom.disable_beforeunload', True)
        # self.driver = webdriver.Firefox(profile)

        self.driver.get(LINKEDIN_URL)

        print('Searching for the Login btn')
        get_by_xpath(self.driver, '//*[@class="login-email"]').send_keys(EMAIL)

        print('Searching for the password btn')
        get_by_xpath(self.driver, '//*[@class="login-password"]').send_keys(PASSWORD)

        print('Searching for the submit')
        get_by_xpath(self.driver, '//*[@id="login-submit"]').click()

    def parse(self, response):
        driver = self.driver

        print('Scrapy parse - get the names list')
        names = driver.find_elements_by_xpath('//ul[@class="browse-map-list"]/li/h4/a')

        frontier = []
        for name in names:
            name.send_keys(Keys.NULL)
            link = name.get_attribute('href')
            frontier.append(scrapy.Request(link, callback=self.parse))

        for f in frontier:
            yield f
