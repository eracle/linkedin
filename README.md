## Linkedin Scraping

[![built with Selenium](https://img.shields.io/badge/built%20with-Selenium-yellow.svg)](https://github.com/SeleniumHQ/selenium)
[![built with Python3](https://img.shields.io/badge/built%20with-Python3-red.svg)](https://www.python.org/)


Scraping software aimed to visit as more linkedin's user pages as possible :-D, the objective is to gain visibility with your account: since LinkedIn notifies the issued User when someone visits his page.

Uses: Scrapy, Selenium web driver, Chromium headless, docker and python3.



### Install
Docker allows very easy and fast run without any pain and tears.

###### 0. Preparations

Install docker from the official website [https://www.docker.com/](https://www.docker.com/)

Install VNC viewer if you do not have one. 
For ubuntu, go for vinagre:

```bash
sudo apt-get update
sudo apt-get install vinagre
```

###### 1. Set your linkedin login and password

Open `conf.py` and fill the quotes with your credentials.

###### 2. Run and build containers with docker-compose

First you need to open your terminal, move to the root folder (usually with the `cd` command) of the project and then type:

```bash
docker-compose up -d --build
```


###### 3. See what your bot can do right now

Open vinagre, and type address and port `localhost:5900`. The password is `secret`.
or otherwise:
```bash
vinagre localhost:5900
```

###### 4. Stop the scraper

Use your terminal again, type in the same window:
```bash
docker-compose down
```


###### Test & Development:

Create the selenium server:
```bash
    make dev
    
    
    virtualenvs -p python3.6 .venv
    source .venv/bin/activate
    pip install -r requirements.txt
```
- Test
```bash
    python -m unittest linkedin/tests.py
```
- Development:
```bash
    scrapy crawl linkedin -a selenium_hostname=localhost
```
or
```bash
    scrapy crawl companies -a selenium_hostname=localhost
```

###### Stop and delete selenium server:
```bash
docker stop $(docker ps -aq --filter name=selenium)

docker rm $(docker ps -aq --filter name=selenium)
```
