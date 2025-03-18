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

# 🔹 STEP 3: EXTRACT FINANCIAL DATA FROM XBRL
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

    # ✅ Identify the correct namespace dynamically
    possible_prefixes = list(namespaces.keys())
    ns_prefixes = [p for p in possible_prefixes if p and p not in ["xsi", "xbrldi", "xlink", "iso4217", "link", "dei"]]

    # ✅ Search Revenue across ALL detected namespaces
    revenue_tags = [
        "Revenue", "Revenues", "SalesRevenueNet", "TotalRevenue",
        "OperatingRevenue", "OperatingRevenues", "TotalNetSales",
        "RevenuesFromContractsWithCustomers"
    ]

    financials = {}
    for ns in ns_prefixes:
        for tag in revenue_tags:
            values = root.xpath(f"//*[local-name()='{tag}']/text()", namespaces=namespaces)
            if values:
                financials["Revenue"] = values[-1].replace(",", "")
                break
        if "Revenue" in financials:
            break  # ✅ Stop if we found it

    # ✅ Debugging: Print Available Tags if Revenue is Missing
    if "Revenue" not in financials:
        all_tags = {etree.QName(el).localname for el in root.iter()}
        print(f"⚠️ WARNING: Revenue missing! Available tags: {all_tags}")

    # ✅ Compute Debt
    debt_tags = [
        "LongTermDebt", "LongTermDebtNoncurrent", "ShortTermBorrowings",
        "NotesPayableCurrent", "DebtInstrument", "DebtObligations"
    ]
    total_debt = sum([
        float(value[0].replace(",", "")) for tag in debt_tags
        if (value := root.xpath(f"//*[local-name()='{tag}']/text()", namespaces=namespaces))
    ]) if any(root.xpath(f"//*[local-name()='{tag}']", namespaces=namespaces)) else 0

    financials["Debt"] = str(int(total_debt)) if total_debt > 0 else "N/A"

    print(f"✅ DEBUG: Extracted financials: {financials}")
    return financials
