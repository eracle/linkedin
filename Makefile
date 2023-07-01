.DEFAULT_GOAL := help

help:
	@perl -nle'print $& if m{^[a-zA-Z_-]+:.*?## .*$$}' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}'

dev: ## run the dev local env
	docker run -p 4444:4444 -p 5900:5900 --publish-all --shm-size="128M" selenium/standalone-chrome-debug

view: ## view the Selenium browser's activity
	vinagre localhost:5900

companies: ## run the 'companies' Scrapy spider
	scrapy crawl companies -a selenium_hostname=localhost -o users.csv

random: ## run the 'random' Scrapy spider
	scrapy crawl random -a selenium_hostname=localhost -o users.csv

byname: ## run the 'byname' Scrapy spider
	scrapy crawl byname -a selenium_hostname=localhost -o users.csv

test: ## run Pytest on the 'linkedin/tests/*' directory
	pytest linkedin/tests/*

attach: ## follow the logs of the 'scrapy' service
	docker-compose logs -f scrapy

stop: ## stop all services defined in Docker Compose
	docker-compose stop

build: ## build all services defined in Docker Compose
	docker-compose build

up: build ## build and start all services defined in Docker Compose
	docker-compose up
