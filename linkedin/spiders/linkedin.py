from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider
from scrapy.spiders import Rule

from linkedin.spiders.selenium import SeleniumSpiderMixin

NETWORK_URL = 'https://www.linkedin.com/mynetwork/invite-connect/connections/'
HOME = 'https://it.linkedin.com/in/antonio-ercole-de-luca-1973401b'


class Linkedin(SeleniumSpiderMixin, CrawlSpider):
    name = "linkedin"
    start_urls = [
        NETWORK_URL,
        HOME,
    ]

    rules = (
        # Extract links matching a single user
        Rule(LinkExtractor(allow=('https:\/\/.*\/in\/.*',), deny=('https:\/\/.*\/in\/edit\/.*',)),
             ),
    )



