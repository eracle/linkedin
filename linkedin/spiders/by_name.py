import urllib.parse

from scrapy import Request

from linkedin.spiders.search import SearchSpider

NAMES_FILE = 'names.txt'


def name_not_matching_stop_criteria(user, name):
    name_set = set(name.lower().strip().split())

    lastName = user['lastName']
    firstName = user['firstName']
    user_name_set = set(lastName.lower().strip().split() + firstName.lower().strip().split())

    return not name_set.issubset(user_name_set)


class ByNameSpider(SearchSpider):
    """
    Spider who searches People by name.
    """
    name = 'byname'
    allowed_domains = ['www.linkedin.com']

    start_urls = []

    names = filter(None, (line.rstrip() for line in open(NAMES_FILE, "rt")))

    def start_requests(self):
        for name in self.names:
            encoded_name = urllib.parse.quote(name.lower())
            url = f"https://www.linkedin.com/search/results/people/?origin=GLOBAL_SEARCH_HEADER&keywords={encoded_name}&page=1"

            yield Request(url=url,
                          callback=super().parser_search_results_page,
                          dont_filter=True,
                          meta={'max_page': 1,
                                'stop_criteria': name_not_matching_stop_criteria,
                                'stop_criteria_args': name,
                                },
                          )

    def wait_page_completion(self, driver):
        """
        Abstract function, used to customize how the specific spider must wait for a search page completion.
        Blank by default
        :param driver:
        :return:
        """
        pass
