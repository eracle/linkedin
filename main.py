import logging
from linkedin.actions.search import search

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    results = search(keyword="software engineer", max_results=5)
    logging.info(f"Found {len(results)} results.")
    for result in results:
        logging.info(result)
