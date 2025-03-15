import requests
import json
from lxml import etree

def find_xbrl_url(index_url):
    """Finds the XBRL file URL from an SEC index.json."""
    headers = {"User-Agent": "Lars Wallin lars.e.wallin@gmail.com"}
    response = requests.get(index_url, headers=headers, timeout=5)  # ✅ Prevent long waits

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
    """Parses XBRL data to extract key financial metrics using efficient parsing."""
    if not xbrl_url or "XBRL file not found" in xbrl_url:
        print(f"❌ ERROR: Invalid XBRL URL: {xbrl_url}")
        return {}

    headers = {"User-Agent": "Lars Wallin lars.e.wallin@gmail.com"}
    response = requests.get(xbrl_url, headers=headers, timeout=5)  # ✅ Shorter timeout

    if response.status_code != 200:
        print(f"❌ ERROR: Failed to fetch XBRL file: {xbrl_url}")
        return {}

    try:
        context = etree.iterparse(response.content, events=("end",), tag="us-gaap:*")  # ✅ Optimized XML parsing
    except etree.XMLSyntaxError as e:
        print(f"❌ ERROR: XML parsing failed: {e}")
        return {}

    financials = {}

    # ✅ Relevant Debt Definitions (ONLY IMPORTANT ONES)
    long_term_debt_tags = ["LongTermDebtNoncurrent", "LongTermDebt"]
    short_term_debt_tags = ["NotesPayableCurrent", "ShortTermBorrowings"]

    # ✅ Map Alternative Names for US GAAP & IFRS
    key_mappings = {
        "Revenue": ["Revenue", "Revenues", "SalesRevenueNet", "TotalRevenue"],
        "NetIncome": ["NetIncomeLoss", "ProfitLoss", "OperatingIncomeLoss"],
        "TotalAssets": ["Assets"],
        "TotalLiabilities": ["Liabilities"],
        "OperatingCashFlow": [
            "CashFlowsFromOperatingActivities",
            "NetCashProvidedByUsedInOperatingActivities",
            "CashGeneratedFromOperations",
            "NetCashFlowsOperating"
        ],
        "CurrentAssets": ["AssetsCurrent", "CurrentAssets"],
        "CurrentLiabilities": ["LiabilitiesCurrent", "CurrentLiabilities"]
    }

    # ✅ Initialize Debt Components
    long_term_debt = 0
    short_term_debt = 0

    for event, elem in context:
        tag_name = etree.QName(elem).localname  # ✅ Extract local name
        value = elem.text.strip() if elem.text else "N/A"

        for key, tags in key_mappings.items():
            if tag_name in tags:
                financials[key] = value

        if tag_name in long_term_debt_tags:
            try:
                long_term_debt += float(value.replace(",", ""))
            except ValueError:
                pass

        if tag_name in short_term_debt_tags:
            try:
                short_term_debt += float(value.replace(",", ""))
            except ValueError:
                pass

        elem.clear()  # ✅ Free memory

    # ✅ Final Debt Calculation
    total_debt = long_term_debt + short_term_debt
    financials["Debt"] = str(int(total_debt)) if total_debt > 0 else "N/A"
    financials["TotalDebt"] = financials["Debt"]  # ✅ Keep TotalDebt the same

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
