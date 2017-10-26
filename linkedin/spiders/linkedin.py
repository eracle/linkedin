from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider
from scrapy.spiders import Rule

from conf import EMAIL, PASSWORD
from linkedin.selenium_utils import get_by_xpath, init_chromium

LINKEDIN_DOMAIN_URL = 'https://it.linkedin.com/'
NETWORK_URL = 'https://www.linkedin.com/mynetwork/invite-connect/connections/'
HOME = 'https://it.linkedin.com/in/antonio-ercole-de-luca-1973401b'


class Linkedin(CrawlSpider):
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

    def __init__(self, host='selenium', *a, **kw):
        self.driver = init_chromium(host)

        # Stop web page from asking me if really want to leave - past implementation, FIREFOX
        # profile = webdriver.FirefoxProfile()
        # profile.set_preference('dom.disable_beforeunload', True)
        # self.driver = webdriver.Firefox(profile)

        self.driver.get(LINKEDIN_DOMAIN_URL)

        print('Searching for the Login btn')
        get_by_xpath(self.driver, '//*[@class="login-email"]').send_keys(EMAIL)

        print('Searching for the password btn')
        get_by_xpath(self.driver, '//*[@class="login-password"]').send_keys(PASSWORD)

        print('Searching for the submit')
        get_by_xpath(self.driver, '//*[@id="login-submit"]').click()

        super().__init__(*a, **kw)
