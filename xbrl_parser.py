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

import requests
from lxml import etree

def extract_summary(xbrl_url):
    """Parses XBRL data to extract key financial metrics, supporting IFRS & US-GAAP."""
    import requests
    from lxml import etree

    if "XBRL file not found" in xbrl_url:
        return {}

    headers = {"User-Agent": "Lars Wallin lars.e.wallin@gmail.com"}
    response = requests.get(xbrl_url, headers=headers)

    if response.status_code != 200:
        return {}

    root = etree.fromstring(response.content)

    # ✅ Define both US-GAAP & IFRS namespaces
    namespaces = {
        "us-gaap": "http://fasb.org/us-gaap/2024",
        "ifrs": "http://xbrl.ifrs.org/taxonomy/2024",
        "x": "http://www.xbrl.org/2003/instance"
    }

    def get_value(tag):
        """Extracts value from XBRL, checking IFRS first, then US-GAAP."""
        value = root.xpath(f"//ifrs:{tag} | //us-gaap:{tag}", namespaces=namespaces)
        return value[0].text if value else "N/A"

    return {
        "Revenue": get_value("Revenue"),
        "NetIncome": get_value("ProfitLoss"),  # IFRS uses "ProfitLoss" instead of "NetIncome"
        "TotalAssets": get_value("Assets"),
        "TotalLiabilities": get_value("Liabilities"),
        "OperatingCashFlow": get_value("CashFlowsFromOperatingActivities"),
        "CurrentAssets": get_value("CurrentAssets"),
        "CurrentLiabilities": get_value("CurrentLiabilities"),
        "Debt": get_value("NoncurrentLiabilities"),
    }

def extract_xbrl_value(tree, tag, ns=None):
    """Extracts the value of a specific XBRL financial tag using namespace handling."""
    try:
        # Handle cases where no namespace is provided
        if ns is None:
            ns = {}

        xpath_query = f"//*[local-name()='{tag}']"
        value = tree.xpath(xpath_query + "/text()", namespaces=ns)
        
        if value:
            extracted_value = value[0]
            print(f"✅ DEBUG: Found {tag}: {extracted_value}")
            return extracted_value
        else:
            print(f"⚠️ WARNING: {tag} not found in XBRL document.")
            return "N/A"

    except Exception as e:
        print(f"❌ ERROR: Could not extract {tag}: {str(e)}")
        return "N/A"
