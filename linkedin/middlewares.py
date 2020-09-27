
from scrapy.http import HtmlResponse
from scrapy.utils.python import to_bytes

from linkedin.spiders.selenium import init_chromium


class SeleniumDownloaderMiddleware:

    def process_request(self, request, spider):
        cookies = spider.cookies
        driver = init_chromium(spider.selenium_hostname, cookies)

        print('SeleniumMiddleware - getting the page')
        driver.get(request.url)

        # request.meta['driver'] = self.driver  # to access driver from response

        print('waiting for page loading')
        spider.wait_page_completion(driver=driver)

        print('SeleniumMiddleware - retrieving body')
        body = to_bytes(driver.page_source)  # body must be of type bytes

        request.meta['driver'] = driver
        return HtmlResponse(driver.current_url, body=body, encoding='utf-8', request=request)

