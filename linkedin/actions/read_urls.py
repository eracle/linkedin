import csv
import os
from typing import Dict, Any, List


def read_urls(linkedin_url: str, params: Dict[str, Any]) -> List[str]:
    """
    Parses input CSVs and returns a list of URLs.
    """
    file_path = params.get('file_path')
    if not file_path or not os.path.exists(file_path):
        print(f"ACTION: read_urls - File not found at {file_path}")
        return []

    print(f"ACTION: read_urls from {file_path}")
    urls = []
    with open(file_path, 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if 'url' in row:
                urls.append(row['url'])

    return urls
