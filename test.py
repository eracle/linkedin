import unittest

from linkedin.selenium_utils import init_chromium


class TestChromium(unittest.TestCase):

    def test_init(self):
        webdriver = init_chromium('localhost')
        self.assertIsNotNone(webdriver)
        print("type: %s" % type(webdriver))
        webdriver.close()

if __name__ == '__main__':
    unittest.main()
