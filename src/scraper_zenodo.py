import requests

BASE_URL = "https://zenodo.org/api/records"

def search_zenodo(query="qdpx OR qpdx", size=5):
    """
    Search Zenodo for records containing QDA files.
    Returns a list of records.
    """

    params = {
        "q": query,
        "size": size
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=30)

        if response.status_code != 200:
            print("Error fetching data from Zenodo")
            return []

        data = response.json()
        records = data.get("hits", {}).get("hits", [])

        print(f"Found {len(records)} records from Zenodo.")
        return records

    except Exception as e:
        print(f"Error during Zenodo search: {e}")
        return []