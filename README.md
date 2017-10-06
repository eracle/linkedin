# Linkedin Scraping
Ubuntu, python3.

Scraping software aimed to simply visit as more pages of the linkedin users as possible, the purpose is to gain visibility: since LinkedIn notifies a user visits to users.

Uses: Scrapy, Selenium web driver, Chromium and python 3.



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




##### Test:
```bash

python -m unittest selenium_chromium/test.py

```
