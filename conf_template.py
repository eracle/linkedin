import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logging.getLogger('scrapy').setLevel(logging.WARNING)

logging.getLogger('selenium').setLevel(logging.WARNING)


EMAIL = ''
PASSWORD = ''
