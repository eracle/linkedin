from scrapy.http import HtmlResponse
from selenium_utils import *
import linkedin
from scrapy.utils.python import to_bytes

class Selenium(object):
    def process_request(self, request, spider):
        driver = spider.driver

        logger.info('SeleniumMiddleware - getting the page')
        driver.get(request.url)

        logger.info('SeleniumMiddleware - click more options')
        more_option = get_by_xpath(driver, '//div/div/button[@class="more-options dropdown-caret"]')
        more_option.send_keys(Keys.NULL)
        more_option.click()

        logger.info('SeleniumMiddleware - wait for names')
        name = get_by_xpath(driver, '//ul[@class="browse-map-list"]/li/h4/a')
        name.send_keys(Keys.NULL)

        #request.meta['driver'] = self.driver  # to access driver from response

        logging.info('SeleniumMiddleware - retrieving body')
        body = to_bytes(driver.page_source)  # body must be of type bytes
        return HtmlResponse(driver.current_url, body=body, encoding='utf-8', request=request)

