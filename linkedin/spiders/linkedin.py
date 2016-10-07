import scrapy

from selenium_utils import *
import random


class Linkedin(scrapy.Spider):
    name = "linkedin"
    start_urls = ['https://www.linkedin.com/in/ludovica-rain%C3%B2-8a1055113?authType=NAME_SEARCH&authToken=E2lZ&trk=tyah&trkInfo=clickedVertical%3Amynetwork%2CentityType%3AentityHistoryName%2CclickedEntityId%3Amynetwork_474885049%2Cidx%3A8']


    def __init__(self):
        logger.info('Init Firefox Browser')
        profile = webdriver.FirefoxProfile()
        profile.set_preference('dom.disable_beforeunload', True)
        self.driver = webdriver.Firefox(profile)

        self.driver.get('https://it.linkedin.com/')

        logger.info('Searching for the Login btn')
        get_by_xpath(self.driver, '//*[@class="login-email"]').send_keys(email)

        logger.info('Searching for the password btn')
        get_by_xpath(self.driver, '//*[@class="login-password"]').send_keys(password)

        logger.info('Searching for the submit')
        get_by_xpath(self.driver, '//*[@id="login-submit"]').click()


    def parse(self, response):
        driver = self.driver

        logger.info('Scrapy parse - get the names list')
        names = driver.find_elements_by_xpath('//ul[@class="browse-map-list"]/li/h4/a')

        frontier = []
        for name in names:
            name.send_keys(Keys.NULL)
            link = name.get_attribute('href')
            frontier.append(scrapy.Request(link, callback=self.parse))

        for f in frontier:
            yield f




