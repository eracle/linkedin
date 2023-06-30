# Set the default goal or default command to be executed when you run `make` without arguments. In this case, the default command is `help`.
.DEFAULT_GOAL := help

# Display a help message with a list of available commands and their descriptions.
help:
	@perl -nle'print $& if m{^[a-zA-Z_-]+:.*?## .*$$}' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}'

# Run the development environment locally. This command uses Docker to run a Selenium standalone Chrome debug container, with specific ports and shared memory size.
dev: ## run the dev local env
	docker run -p 4444:4444 -p 5900:5900 --publish-all --shm-size="128M" selenium/standalone-chrome-debug

# Open a remote desktop viewer (Vinagre) to view the Selenium browser's activity on localhost at port 5900.
view: ## view the Selenium browser's activity
	vinagre localhost:5900

# Run a Scrapy spider named 'companies', passing 'localhost' as the Selenium hostname and outputting the results to 'users.csv'.
companies: ## run the 'companies' Scrapy spider
	scrapy crawl companies -a selenium_hostname=localhost -o users.csv

# Run a Scrapy spider named 'random', passing 'localhost' as the Selenium hostname and outputting the results to 'users.csv'.
random: ## run the 'random' Scrapy spider
	scrapy crawl random -a selenium_hostname=localhost -o users.csv

# Run a Scrapy spider named 'byname', passing 'localhost' as the Selenium hostname and outputting the results to 'users.csv'.
byname: ## run the 'byname' Scrapy spider
	scrapy crawl byname -a selenium_hostname=localhost -o users.csv

# Run Pytest on the 'linkedin/tests/*' directory to execute all test cases.
tests: ## run Pytest on the 'linkedin/tests/*' directory
	pytest linkedin/tests/*

# Follow the logs of the 'scrapy' service in your Docker Compose setup.
attach: ## follow the logs of the 'scrapy' service
	docker-compose logs -f scrapy

# Stop all services defined in your Docker Compose file.
stop: ## stop all services defined in Docker Compose
	docker-compose stop

# Build all services defined in your Docker Compose file.
build: ## build all services defined in Docker Compose
	docker-compose build

# First build all services defined in your Docker Compose file (using the `build` command), then start all services.
up: build ## build and start all services defined in Docker Compose
	docker-compose up
