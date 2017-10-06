import unittest

from selenium_chromium import init_chromium


class TestChromium(unittest.TestCase):

    def test_init(self):
        webdriver = init_chromium(False)
        self.assertIsNotNone(webdriver)


if __name__ == '__main__':
    unittest.main()
