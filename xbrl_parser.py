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
                    return value[0].text
            except etree.XPathEvalError:
                continue  # Move to the next namespace

        # ✅ Handle cases where NO namespace is used
        xpath_query = f"//*[local-name()='{tag}']"
        value = root.xpath(xpath_query + "/text()", namespaces=namespaces)
        if value:
            print(f"✅ DEBUG: Found {tag} (No Namespace): {value[0]}")
            return value[0]

        print(f"⚠️ WARNING: {tag} not found in any namespace.")
        return "N/A"

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
        if ns is None:
            ns = {}

        # ✅ Use namespace-independent lookup if needed
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
