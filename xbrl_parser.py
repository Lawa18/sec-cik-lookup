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

    namespaces = {k if k else "default": v for k, v in root.nsmap.items()}  # ✅ Avoid empty namespace issues
    print(f"✅ DEBUG: Extracted Namespaces from XBRL: {namespaces}")

    def get_value(*tags):
        """Extracts financial values using dynamic namespace detection."""
        possible_tags = []
        
        for tag in tags:
            possible_tags.extend([
                f"{ns_prefix}:{tag}" if ns_prefix else tag for ns_prefix in namespaces.keys()
            ])
            possible_tags.append(tag)  # Add raw tag as last fallback
        
        for tag_variant in possible_tags:
            value = root.xpath(f"//*[local-name()='{tag_variant}']/text()", namespaces=namespaces)
            if value:
                return value[0]  # ✅ Return first match found
        
        return "N/A"  # Default if no match

    financials = {
        "Revenue": get_value("Revenue", "Revenues", "SalesRevenueNet", "TotalRevenue"),  # IFRS & US GAAP variations
        "NetIncome": get_value("NetIncomeLoss", "ProfitLoss", "OperatingIncomeLoss"),  # Profit/Loss variations
        "TotalAssets": get_value("Assets"),
        "TotalLiabilities": get_value("Liabilities"),
        "OperatingCashFlow": get_value("CashFlowsFromOperatingActivities", "NetCashProvidedByUsedInOperatingActivities"),
        "CurrentAssets": get_value("AssetsCurrent"),
        "CurrentLiabilities": get_value("LiabilitiesCurrent"),
        "Debt": get_value("LongTermDebtNoncurrent", "DebtCurrent", "ShortTermDebt")  # Debt variations
    }

    print(f"✅ DEBUG: Extracted financials: {financials}")  # ✅ Debug print

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
        
