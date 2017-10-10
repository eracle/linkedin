# Linkedin Scraping
Ubuntu, python3.

Scraping software aimed to visit as more pages of the linkedin users as possible, the purpose is to gain visibility: since LinkedIn notifies when you visit another user page.

Uses: Scrapy, Selenium web driver, Chromium headless and python3.

Tested on Ubuntu 16.04.2 LTS


# Install

```bash
virtualenv -p python3 .venv
source .venv/bin/activate

pip install -r requirements.txt

```
# Usage:
Rename the conf_template.py to conf.py, modify it with linkein username and password and type:

```bash
scrapy crawl linkedin
```

Instead, for use chrome headless:
```bash
scrapy crawl linkedin -a headless=True
```



##### Test:
```bash

python -m unittest selenium_chromium/test.py

```
