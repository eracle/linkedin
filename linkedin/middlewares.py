from scrapy.http import HtmlResponse
from scrapy.utils.python import to_bytes


from .selenium_utils import get_by_xpath


class Selenium(object):
    def process_request(self, request, spider):
        driver = spider.driver

        print('SeleniumMiddleware - getting the page')
        driver.get(request.url)

        # print('SeleniumMiddleware - click more options')
        # more_option = get_by_xpath(driver, '//div/div/button[@class="more-options dropdown-caret"]')
        # more_option.send_keys(Keys.NULL)
        # more_option.click()
        # print('SeleniumMiddleware - wait for names')
        # name = get_by_xpath(driver, '//ul[@class="browse-map-list"]/li/h4/a')
        # name.send_keys(Keys.NULL)

        # request.meta['driver'] = self.driver  # to access driver from response

        print('waiting for page loading')
        profile_xpath = "//*[@id='nav-settings__dropdown-trigger']/img"
        get_by_xpath(driver, profile_xpath)

        print('SeleniumMiddleware - retrieving body')
        body = to_bytes(driver.page_source)  # body must be of type bytes
        return HtmlResponse(driver.current_url, body=body, encoding='utf-8', request=request)

