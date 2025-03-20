import requests
import time
import json
from lxml import etree

# ✅ SEC API Rate Limit (~8-10 requests/sec)
REQUEST_DELAY = 0.5  # 500ms delay per request
MAX_RETRIES = 3  # Retry up to 3 times if request fails
RETRY_DELAY = 3  # Wait 3 sec before retrying failed requests

# ✅ Standard Headers
HEADERS = {"User-Agent": "Lars Wallin lars.e.wallin@gmail.com"}

# 🔹 STEP 1: FIND XBRL URL
def find_xbrl_url(index_url):
    """Finds the XBRL file URL from an SEC index.json."""
    time.sleep(REQUEST_DELAY)  # ✅ Prevent SEC rate limit issues

    response = requests.get(index_url, headers=HEADERS, timeout=5)
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

# 🔹 STEP 2: FETCH DATA WITH RETRIES
def fetch_with_retries(url):
    """Fetches data from the SEC API with retries."""
    for attempt in range(MAX_RETRIES):
        response = requests.get(url, headers=HEADERS, timeout=5)

        if response.status_code == 200:
            return response.json()  # ✅ Success
        elif response.status_code == 403:
            print(f"⚠️ WARNING: SEC API rate limit hit. Retrying in {RETRY_DELAY} sec...")
        elif response.status_code == 500:
            print(f"❌ ERROR: SEC API is down. Retrying in {RETRY_DELAY} sec...")

        time.sleep(RETRY_DELAY)  # ✅ Wait before retrying

    print("❌ ERROR: SEC API failed after multiple attempts.")
    return None  # Return None if all attempts fail

# 🔹 STEP 3: DEBUG FUNCTION TO IDENTIFY REVENUE TAGS
def debug_revenue_tags(root):
    """Prints all available XBRL tags related to Revenue."""
    available_tags = {etree.QName(elem).localname for elem in root.iter()}
    revenue_tags = [tag for tag in available_tags if "revenue" in tag.lower()]
    
    if revenue_tags:
        print(f"🔍 DEBUG: Possible Revenue tags found in XBRL: {revenue_tags}")
    else:
        print("⚠️ WARNING: No Revenue-related tags found in XBRL.")

# 🔹 STEP 4: EXTRACT FINANCIAL DATA FROM XBRL
def extract_summary(xbrl_url):
    """Parses XBRL data to extract key financial metrics."""
    if not xbrl_url:
        print(f"❌ ERROR: Invalid XBRL URL: {xbrl_url}")
        return {}

    time.sleep(REQUEST_DELAY)  # ✅ Prevent SEC rate limit issues
    response = requests.get(xbrl_url, headers=HEADERS, timeout=5)

    if response.status_code != 200:
        print(f"❌ ERROR: Failed to fetch XBRL file: {xbrl_url}")
        return {}

    try:
        root = etree.fromstring(response.content)  # ✅ Proper XML Parsing
    except etree.XMLSyntaxError as e:
        print(f"❌ ERROR: XML parsing failed: {e}")
        return {}

    namespaces = {k if k else "default": v for k, v in root.nsmap.items()}  
    print(f"✅ DEBUG: Extracted Namespaces from XBRL: {namespaces}")

    # ✅ **Extract Revenue (Prioritize Correct Tags)**
    revenue_value = None
    debug_revenue_tags(root)  # ✅ Print all available revenue-related tags

    revenue_candidates = {}
    for tag in root.iter():
        tag_name = etree.QName(tag).localname
        if "revenue" in tag_name.lower():
            revenue_candidates[tag_name] = tag.text.strip() if tag.text else "N/A"

    # ✅ Print all found Revenue values
    print(f"🔍 DEBUG: Extracted Revenue Candidates (Before Filtering): {revenue_candidates}")

    # ✅ Exclude incorrect revenue tags
    exclude_revenue_tags = {"RevenueFromContractWithCustomerExcludingAssessedTax", "RevenueFromContractWithCustomerPolicyTextBlock"}

    # ✅ Select correct revenue value
    for tag, value in revenue_candidates.items():
        if tag not in exclude_revenue_tags and value != "N/A":
            revenue_value = value
            print(f"✅ DEBUG: Selected Revenue: {revenue_value} (Tag: {tag})")
            break

    # ✅ Compute Debt
    debt_tags = [
        "LongTermDebt", "LongTermDebtNoncurrent", "ShortTermBorrowings",
        "NotesPayableCurrent", "DebtInstrument", "DebtObligations"
    ]
    
    total_debt = 0
    for tag in debt_tags:
        values = root.xpath(f"//*[local-name()='{tag}']/text()", namespaces=namespaces)
        if values:
            try:
                total_debt += float(values[0].replace(",", ""))
            except ValueError:
                pass

    # ✅ Extract Other Financials
    key_mappings = {
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
        "CurrentLiabilities": ["LiabilitiesCurrent", "CurrentLiabilities"],
        "CashPosition": [
            "CashAndCashEquivalentsAtCarryingValue",
            "CashAndCashEquivalents",
            "CashCashEquivalentsAndShortTermInvestments",
            "CashAndShortTermInvestments",
            "CashEquivalents"
        ]
    }

    financials = {"Revenue": revenue_value if revenue_value else "N/A"}

    # ✅ Extract Other Key Financials
    for key, tags in key_mappings.items():
        for tag in tags:
            values = root.xpath(f"//*[local-name()='{tag}']/text()", namespaces=namespaces)
            if values:
                financials[key] = values[-1].replace(",", "")
                break  # ✅ Stop at first match

    # ✅ Assign Debt Value
    financials["Debt"] = str(int(total_debt)) if total_debt > 0 else "N/A"

    print(f"✅ DEBUG: Extracted financials: {financials}")
    return financials
