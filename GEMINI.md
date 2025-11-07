
# GEMINI.md

## Project Overview

This project is a LinkedIn automation tool designed to automate various tasks on the LinkedIn platform. It utilizes Playwright for browser automation, with a stealth mode to minimize the risk of detection. The tool is containerized using Docker and includes a VNC server for visual debugging of the automation process.

The core functionalities of the tool, as described in the README, include:

*   **Automation Engine**: Using Playwright for browser automation.
*   **Campaigns**: Executing sequences of actions from YAML configuration.
*   **Scheduling**: Queuing actions for future execution.
*   **Local Database**: Storing scraped data and logs in DuckDB or SQLite.
*   **AI-powered Messaging**: Generating personalized messages using AI models.
*   **Analytics**: Tracking key performance metrics.


## Building and Running

The project is managed using Docker Compose and a `Makefile`.

*   **Build the Docker containers**:
    ```bash
    make build
    ```
*   **Start the application**:
    ```bash
    make up
    ```
*   **Stop the application**:
    ```bash
    make stop
    ```
*   **View logs**:
    ```bash
    make attach
    ```

The `docker-compose.yml` file (`local.yml`) defines the `app` service that runs the LinkedIn automation.

To view the browser automation, you can use a VNC viewer on your host machine to connect to `localhost:5900`.

## Development Conventions

### Dependencies

The main Python dependencies are `playwright` and `playwright-stealth`. These are installed directly in the `Dockerfile`. The `requirements/base.txt` file is currently empty.

### Configuration

The project's configuration is managed in `linkedin/conf.py`. Currently, it contains hardcoded LinkedIn credentials, which is a security risk. These should be replaced with environment variables.

### Testing

The project uses `pytest` for testing, as indicated by the `pytest.ini` file. However, there are no tests implemented yet.

### Code Style

The code seems to follow the PEP 8 style guide, but there is no linter configured to enforce it.
