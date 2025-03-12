import requests
import json
from lxml import etree

def find_xbrl_url(index_url):
    """Finds the XBRL file URL from an SEC index.json."""
    headers = {"User-Agent": "Lars Wallin lars.e.wallin@gmail.com"}
    response = requests.get(index_url, headers=headers)

    if response.status_code != 200:
        return None

    try:
        data = response.json()
        if "directory" in data and "item" in data["directory"]:
            for file in data["directory"]["item"]:
                if file["name"].endswith(".xml") and "htm.xml" in file["name"]:
                    return index_url.replace("index.json", file["name"])
    except json.JSONDecodeError:
        return None

    return None  # No XBRL file found

def extract_summary(xbrl_url):
    """Parses XBRL data to extract key financial metrics."""
    if not xbrl_url or "XBRL file not found" in xbrl_url:
        return {}

    headers = {"User-Agent": "Lars Wallin lars.e.wallin@gmail.com"}
    response = requests.get(xbrl_url, headers=headers)

    if response.status_code != 200:
        return {}

    root = etree.fromstring(response.content)

    # ✅ Extract available namespaces dynamically
    namespaces = {k: v for k, v in root.nsmap.items() if v}
    print(f"✅ DEBUG: Extracted Namespaces from XBRL: {namespaces}")

    # ✅ Allow multi-namespace search (IFRS, US-GAAP, or Default)
    known_ns = ["ifrs-full", "ifrs", "us-gaap"]
    active_ns = [ns for ns in known_ns if ns in namespaces]

    def get_value(tag):
        """Extracts financial values using multi-namespace detection."""
        for ns in active_ns:  # ✅ Try each known namespace
            xpath_query = f"//{ns}:{tag}"
            try:
                value = root.xpath(xpath_query, namespaces=namespaces)
                if value:
                    print(f"✅ DEBUG: Found {tag} in {ns}: {value[0].text}")
