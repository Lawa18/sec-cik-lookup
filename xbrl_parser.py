import requests
from lxml import etree

def extract_summary(xbrl_url):
    """Parses XBRL data to extract key financial metrics, supporting IFRS & US-GAAP."""
    if "XBRL file not found" in xbrl_url:
        return {}

    headers = {"User-Agent": "Lars Wallin lars.e.wallin@gmail.com"}
    response = requests.get(xbrl_url, headers=headers)

    if response.status_code != 200:
        return {}

    root = etree.fromstring(response.content)

    # ✅ Dynamically Extract All Available Namespaces
    namespaces = {k: v for k, v in root.nsmap.items() if v}
    if "ifrs-full" in namespaces:
        ns_prefix = "ifrs-full"
    elif "ifrs" in namespaces:
        ns_prefix = "ifrs"
    elif "us-gaap" in namespaces:
        ns_prefix = "us-gaap"
    else:
        ns_prefix = "x"  # Default fallback

    def get_value(tag):
        """Extracts value from XBRL, dynamically detecting namespace prefixes."""
        value = root.xpath(f"//{ns_prefix}:{tag}", namespaces=namespaces)
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
