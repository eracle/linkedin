import logging

from scrapy.http import HtmlResponse
from scrapy.utils.python import to_bytes

from linkedin.spiders.selenium import init_chromium

logger = logging.getLogger(__name__)


class SeleniumDownloaderMiddleware:
    def process_request(self, request, spider):
        cookies = spider.cookies
        driver = init_chromium(spider.selenium_hostname, cookies)

        logger.debug(f"{request.url}")
        driver.get(request.url)

        # request.meta['driver'] = self.driver  # to access driver from response

        logger.debug("waiting for page loading")
        spider.wait_page_completion(driver=driver)

        # body must be of type bytes
        body = to_bytes(driver.page_source)
        logger.debug(f"Body size: {len(body)}")

        request.meta["driver"] = driver
        return HtmlResponse(
            driver.current_url, body=body, encoding="utf-8", request=request
        )
