# -*- coding: utf-8 -*-
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import Spider
from scrapy.spiders import Rule

from linkedin.spiders.selenium import SeleniumSpiderMixin

TOYOTA = 'https://www.linkedin.com/company/toyota/'
NISSAN = 'https://www.linkedin.com/company/nissan-motor-corporation/'


class CompaniesSpider(SeleniumSpiderMixin, Spider):
    name = 'companies'
    allowed_domains = ['www.linkedin.com']
    start_urls = [
        TOYOTA,
        # NISSAN,
    ]

    rules = (
        Rule(
            LinkExtractor(
                allow=('https:\/\/www\.linkedin\.com\/search\/results\/people\/\?facetCurrentCompany.*',)),
            # callback='parse_company'
        ),
    )

    def parse(self, response):
        f"""
            This function parses page and follows the "See all * employees on Linkedin" link.

            @url {TOYOTA}
            @returns items 0
            @returns requests 1 1
        """
        return super().parse(response)
