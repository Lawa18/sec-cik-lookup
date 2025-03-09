import requests
from lxml import etree

def find_xbrl_url(index_url):
    """Fetches SEC index.json and finds the correct XBRL file for financial data."""
    headers = {"User-Agent": "Lars Wallin lars.e.wallin@gmail.com"}
    response = requests.get(index_url, headers=headers)

    if response.status_code != 200:
        print(f"ERROR: Failed to fetch index.json. Status: {response.status_code}")
        return None

    try:
        index_data = response.json()
        xbrl_file = None

        # ✅ Prioritize MAIN financial statement XBRL files
        for file in index_data["directory"]["item"]:
            name = file["name"].lower()
            if name.endswith(("_htm.xml", "_full.xml")):
                xbrl_file = f"{index_url.rsplit('/', 1)[0]}/{file['name']}"
                break  

        return xbrl_file

    except Exception as e:
        print(f"ERROR: Could not parse SEC index.json: {e}")
        return None

def extract_summary(xbrl_url):
    """Extracts financial data from XBRL SEC filing."""
    if not xbrl_url:
        return "No XBRL file found."

    headers = {"User-Agent": "Lars Wallin lars.e.wallin@gmail.com"}
    response = requests.get(xbrl_url, headers=headers)

    if response.status_code != 200:
        return f"Error fetching XBRL report. Status: {response.status_code}"

    try:
        parser = etree.XMLParser(recover=True)
        tree = etree.fromstring(response.content, parser=parser)

        financials = {
            "Revenue": extract_xbrl_value(tree, "Revenues"),
            "NetIncome": extract_xbrl_value(tree, "NetIncomeLoss"),
            "TotalAssets": extract_xbrl_value(tree, "Assets"),
            "TotalLiabilities": extract_xbrl_value(tree, "Liabilities"),
            "OperatingCashFlow": extract_xbrl_value(tree, "NetCashProvidedByUsedInOperatingActivities"),
            "CurrentAssets": extract_xbrl_value(tree, "AssetsCurrent"),
            "CurrentLiabilities": extract_xbrl_value(tree, "LiabilitiesCurrent"),
            "Debt": extract_xbrl_value(tree, "LongTermDebtNoncurrent")
        }

        return financials

    except Exception as e:
        return f"Error extracting financial data: {str(e)}"

def extract_xbrl_value(tree, tag):
    """Extracts the value of a specific XBRL financial tag."""
    try:
        value = tree.xpath(f"//*[local-name()='{tag}']/text()")
        return value[0] if value else "N/A"
    except Exception:
        return "N/A"
