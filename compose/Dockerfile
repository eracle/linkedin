# Use the official Playwright Python Docker image as base (pre-includes browsers and deps)
FROM mcr.microsoft.com/playwright/python:v1.55.0-noble

# Define the application directory
ARG APP_HOME=/app
WORKDIR ${APP_HOME}

# Define a build argument to determine which environment to use
ARG BUILD_ENV=production

# Install uv using pip (since the base has pip)
RUN pip install uv

# Copy requirements folder and install the dependencies based on BUILD_ENV using uv
COPY ./requirements /requirements
RUN uv pip install --system -r /requirements/${BUILD_ENV}.txt

# Install Playwright and playwright-stealth using uv (no need for 'playwright install --with-deps' as browsers/deps are pre-installed)
RUN uv pip install --system playwright playwright-stealth

# Copy necessary startup scripts
COPY ./compose/start /start
RUN sed -i 's/\r$//g' /start && chmod +x /start

# Copy the entire application code to the app directory
COPY . ${APP_HOME}

# Set the working directory
WORKDIR ${APP_HOME}