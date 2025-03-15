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
    """Parses XBRL data to extract key financial metrics."""
    if not xbrl_url or "XBRL file not found" in xbrl_url:
        print(f"❌ ERROR: Invalid XBRL URL: {xbrl_url}")
        return {}

    headers = {"User-Agent": "Lars Wallin lars.e.wallin@gmail.com"}
    response = requests.get(xbrl_url, headers=headers, timeout=5)  # ✅ Prevent long waits

    if response.status_code != 200:
        print(f"❌ ERROR: Failed to fetch XBRL file: {xbrl_url}")
        return {}

    try:
        root = etree.fromstring(response.content)  # ✅ FIX: Proper XML Parsing
    except etree.XMLSyntaxError as e:
        print(f"❌ ERROR: XML parsing failed: {e}")
        return {}

    namespaces = {k if k else "default": v for k, v in root.nsmap.items()}  # ✅ Avoid empty namespace issues
    print(f"✅ DEBUG: Extracted Namespaces from XBRL: {namespaces}")

    # ✅ Define mappings for key financial metrics (US GAAP & IFRS variations)
    key_mappings = {
        "Revenue": ["Revenue", "Revenues", "SalesRevenueNet", "TotalRevenue"],
        "NetIncome": ["NetIncomeLoss", "ProfitLoss"],
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

    # ✅ **Expanded Debt Extraction (Covers IFRS & US GAAP)**
    debt_tags = [
        "LongTermDebt", "LongTermDebtNoncurrent", "ShortTermBorrowings",
        "NotesPayableCurrent", "DebtInstrument", "DebtObligations",
        "Borrowings", "LoansPayable", "DebtSecurities",
        "DebtAndFinanceLeases", "FinancialLiabilities", "LeaseLiabilities",
        "ConvertibleDebt", "InterestBearingLoans"
    ]
    
    total_debt = 0  # ✅ Initialize debt sum

    # ✅ Extract financials
    financials = {}
    for key, tags in key_mappings.items():
        for tag in tags:
            value = root.xpath(f"//*[local-name()='{tag}']/text()", namespaces=namespaces)
            if value:
                financials[key] = value[0].replace(",", "")
                break  # ✅ Stop at first match

    # ✅ Calculate Debt (Sum all relevant debt-related tags)
    for tag in debt_tags:
        value = root.xpath(f"//*[local-name()='{tag}']/text()", namespaces=namespaces)
        if value:
            try:
                total_debt += float(value[0].replace(",", ""))
            except ValueError:
                pass

    # ✅ Assign final debt values
    financials["Debt"] = str(int(total_debt)) if total_debt > 0 else "N/A"

    print(f"✅ DEBUG: Extracted financials: {financials}")  # ✅ Debug print
    return financials

def extract_xbrl_value(tree, tag, ns=None):
    """Extracts the value of a specific XBRL financial tag using namespace handling."""
    try:
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
