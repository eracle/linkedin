"""This module contains the ``SeleniumMiddleware`` scrapy middleware"""

import logging
from random import uniform

from scrapy.http import HtmlResponse
from twisted.internet import reactor
from twisted.internet.task import deferLater

logger = logging.getLogger(__name__)


class SeleniumSpiderMixin:
    def sleep(self, delay=None):
        randomize_delay = self.settings.getbool("RANDOMIZE_DOWNLOAD_DELAY")
        delay = delay or self.settings.getint("DOWNLOAD_DELAY")
        if randomize_delay:
            delay = uniform(0.5 * delay, 1.5 * delay)
        logger.debug(f"sleeping for {delay}")
        d = deferLater(reactor, delay, lambda: None)
        d.addErrback(lambda err: logger.error(err))
        return d


class SeleniumMiddleware:
    """Scrapy middleware handling the requests using selenium"""

    def __init__(self):
        self.driver = None

    def process_request(self, request, spider):
        """Process a request using the selenium driver if applicable"""
        self.driver = spider.driver
        spider.sleep()
        self.driver.get(request.url)

        for cookie_name, cookie_value in request.cookies.items():
            self.driver.add_cookie({"name": cookie_name, "value": cookie_value})

        spider.wait_page_completion(self.driver)
        body = str.encode(self.driver.page_source)

        # Expose the driver via the "meta" attribute
        request.meta.update({"driver": self.driver})

        return HtmlResponse(
            self.driver.current_url, body=body, encoding="utf-8", request=request
        )
