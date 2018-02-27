import pytest

from linkedin.spiders.selenium import login, extracts_see_all_url, extracts_linkedin_users, extract_company
from linkedin.tests.selenium import SeleniumTest

NISSAN = 'https://www.linkedin.com/company/nissan-motor-corporation/'
TOYOTA_USERS_LIST = 'https://www.linkedin.com/search/results/people/?facetCurrentCompany=[' \
                    '%222107%22]&origin=FACETED_SEARCH '


class CompaniesTest(SeleniumTest):
    def setUp(self):
        super().setUp()
        login(self.driver)

    #@pytest.mark.skip
    def test_extracts_see_all_url(self):
        self.driver.get(NISSAN)
        url = extracts_see_all_url(self.driver)
        print(url)
        assert url.startswith("https://www.linkedin.com/search/results/people/?facetCurrentCompany=")

    def test_extracts_linkedin_users(self):
        self.driver.get(TOYOTA_USERS_LIST)

        company = extract_company(self.driver)
        self.assertEquals(company, 'Toyota North America')

        users = extracts_linkedin_users(self.driver, company)
        self.assertEquals(len(list(users)), 10)
        for user in users:
            self.assertIsNotNone(user.get('name', None))
            self.assertIsNotNone(user.get('title', None))
            self.assertIsNotNone(user.get('company', None))
