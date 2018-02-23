import unittest
from unittest import skip

from linkedin.spiders.selenium import init_chromium, login, extract_see_all_url

NISSAN = 'https://www.linkedin.com/company/nissan-motor-corporation/'


class TestChromium(unittest.TestCase):

    def setUp(self):
        self.driver = init_chromium('localhost')

    def tearDown(self):
        self.driver.close()

    @skip
    def test_init(self):
        self.assertIsNotNone(self.driver)
        print("type: %s" % type(self.driver))

    @skip
    def test_login(self):
        login(self.driver)

    def test_extract_see_all_url(self):
        login(self.driver)
        self.driver.get(NISSAN)
        url = extract_see_all_url(self.driver)
        print(url)
        assert url.startswith("https://www.linkedin.com/search/results/people/?facetCurrentCompany=")

if __name__ == '__main__':
    unittest.main()
