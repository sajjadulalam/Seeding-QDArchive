import requests

def download_file(url, save_path):
    """
    Download a file from a URL and save it locally.
    """

    # Create folder if it doesn't exist
    save_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        response = requests.get(url, timeout=30)

        if response.status_code == 200:
            with open(save_path, "wb") as f:
                f.write(response.content)

            print(f"Downloaded: {save_path.name}")
        else:
            print(f"Failed to download (status {response.status_code}): {url}")

    except Exception as e:
        print(f"Error downloading {url}: {e}")