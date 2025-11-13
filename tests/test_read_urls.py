import csv
import os
from tempfile import NamedTemporaryFile
from linkedin.actions.read_urls import read_urls

def test_read_urls_from_csv():
    # Create a temporary CSV file
    with NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as temp_csv:
        writer = csv.writer(temp_csv)
        writer.writerow(['url'])
        writer.writerow(['https://www.linkedin.com/in/test-profile-1'])
        writer.writerow(['https://www.linkedin.com/in/test-profile-2'])
        temp_csv_path = temp_csv.name

    # Call the function with the path to the temporary file
    # The read_urls function is not returning anything, so this test will fail
    urls = read_urls(None, {'file_path': temp_csv_path})

    # Assert that the function returns the correct list of URLs
    expected_urls = [
        'https://www.linkedin.com/in/test-profile-1',
        'https://www.linkedin.com/in/test-profile-2'
    ]
    assert urls == expected_urls

    # Clean up the temporary file
    os.unlink(temp_csv_path)
