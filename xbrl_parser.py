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
        print(f"❌ ERROR: Invalid XBRL URL: {xbrl_url}")
        return {}

    headers = {"User-Agent": "Lars Wallin lars.e.wallin@gmail.com"}
    response = requests.get(xbrl_url, headers=headers)

    if response.status_code != 200:
        print(f"❌ ERROR: Failed to fetch XBRL file: {xbrl_url}")
        return {}

    try:
        root = etree.fromstring(response.content)
    except etree.XMLSyntaxError as e:
        print(f"❌ ERROR: XML parsing failed: {e}")
        return {}

    # ✅ Extract all available namespaces dynamically
    namespaces = {k if k else "default": v for k, v in root.nsmap.items()}
    print(f"✅ DEBUG: Extracted Namespaces from XBRL: {namespaces}")

    # ✅ Identify available namespace prefixes
    ns_prefixes = [key for key in namespaces if key in ["us-gaap", "ifrs-full", "dei"]]

    def get_value(tag):
        """Extracts financial values using dynamic namespace detection."""
        for ns_prefix in ns_prefixes:
            xpath_query = f"//{ns_prefix}:{tag}" if ns_prefix else f"//{tag}"
            value = root.xpath(xpath_query, namespaces=namespaces)
            if value:
                return value[0].text  # ✅ Return first match
        
        # ✅ If no match found, attempt namespace-independent lookup
        xpath_query = f"//*[local-name()='{tag}']"
        value = root.xpath(xpath_query + "/text()", namespaces=namespaces)
        return value[0] if value else "N/A"

    financials = {
        "Revenue": get_value("Revenues"),  # US GAAP: "Revenues" | IFRS: "Revenue"
        "NetIncome": get_value("NetIncomeLoss"),  # US GAAP: "NetIncomeLoss" | IFRS: "ProfitLoss"
        "TotalAssets": get_value("Assets"),
        "TotalLiabilities": get_value("Liabilities"),
        "OperatingCashFlow": get_value("CashFlowsFromOperatingActivities"),
        "CurrentAssets": get_value("AssetsCurrent"),
        "CurrentLiabilities": get_value("LiabilitiesCurrent"),
        "Debt": get_value("LongTermDebtNoncurrent"),  # US GAAP: "LongTermDebtNoncurrent"
    }

    print(f"✅ DEBUG: Extracted financials: {financials}")  # ✅ Debugging output
    return financials

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
