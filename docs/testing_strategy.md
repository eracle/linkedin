# Testing Strategy

This document outlines the strategy for testing the LinkedIn automation tool. The goal is to create a testable
architecture that allows for robust and maintainable tests.

## Core Principles

- **Framework**: All tests will be written using the `pytest` framework.
- **Separation of Concerns**: Tests will be separated into `unit` and `integration` tests to distinguish between testing
  pure logic and testing interactions with external systems.
- **Mocking**: External dependencies (database, APIs, Playwright) will be mocked in unit tests to ensure they are fast,
  reliable, and isolated.

## Unit Tests

Unit tests will focus on the business logic of individual components.

- **Workflow Engine (`workflows.py`)**: The logic of the workflow orchestrator will be tested by mocking the `actions`
  and `database` modules. We can assert that for a given campaign, the engine calls the correct action functions in the
  correct order, without executing their real logic.
- **Campaign Parser (`campaign_parser.py`)**: We can test the YAML parsing and Pydantic validation logic with sample
  valid and invalid campaign files.

## Integration Tests

Integration tests will verify the interaction between components and with external systems in a controlled environment.

- **Database (`database.py`)**: The database module will be tested against a real (but temporary or in-memory) SQLite
  database to ensure that SQL queries are correct and data is stored and retrieved as expected.
- **Actions (`actions.py`)**: In the future, when action logic is implemented, we may have a separate suite of
  integration tests that run against mock API servers or in a controlled browser environment to test Playwright
  interactions.

## Tools for Future Implementation

- **`pytest-mock`**: For mocking dependencies during unit testing.
- **`factory_boy`**: For generating test data and populating the test database with `Profile` and `Company` objects,
  making tests easier to write and maintain.

By following this strategy, we can build a comprehensive test suite that ensures the reliability and correctness of the
application while keeping the tests fast and easy to manage.
