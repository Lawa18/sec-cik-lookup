import requests
import time
import json

# ✅ SEC API Rate Limit (~8-10 requests/sec)
REQUEST_DELAY = 0.5
MAX_RETRIES = 5
RETRY_DELAY = 5
TIMEOUT = 10

# ✅ Standard Headers
HEADERS = {"User-Agent": "Lars Wallin lars.e.wallin@gmail.com"}

# 🔹 STEP 1: FETCH DATA WITH IMPROVED ERROR HANDLING
def fetch_with_retries(url):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            if response.status_code == 200:
                return response.json()
            elif response.status_code in [403, 500, 503]:
                time.sleep(RETRY_DELAY)
            else:
                break
        except requests.exceptions.Timeout:
            time.sleep(RETRY_DELAY)
        except requests.exceptions.RequestException:
            time.sleep(RETRY_DELAY)
    return None

# 🔹 STEP 2: FIND XBRL URL
def find_xbrl_url(index_url):
    time.sleep(REQUEST_DELAY)
    response = fetch_with_retries(index_url)
    if not response:
        return None
    try:
        if "directory" in response and "item" in response["directory"]:
            for file in response["directory"]["item"]:
                if file["name"].endswith(".xml") and "htm.xml" in file["name"]:
                    return index_url.replace("index.json", file["name"])
    except json.JSONDecodeError:
        return None
    return None
