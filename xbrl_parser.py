import requests
import time
import json
from lxml import etree

# ✅ SEC API Rate Limit (~8-10 requests/sec)
REQUEST_DELAY = 0.5  # 500ms delay per request
MAX_RETRIES = 5  # Retry up to 5 times if request fails
RETRY_DELAY = 5  # Wait 5 sec before retrying failed requests
TIMEOUT = 10  # Increase API timeout

# ✅ Standard Headers
HEADERS = {"User-Agent": "Lars Wallin lars.e.wallin@gmail.com"}

# 🔹 STEP 1: FETCH DATA WITH IMPROVED ERROR HANDLING
def fetch_with_retries(url):
    """Fetches data from the SEC API with retries & improved error handling."""
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code in [403, 500, 503]:
                print(f"⚠️ WARNING: SEC API rate limit hit or server issue. Retrying in {RETRY_DELAY} sec (Attempt {attempt}/{MAX_RETRIES})...")
                time.sleep(RETRY_DELAY)
            else:
                print(f"❌ ERROR: Unexpected API response ({response.status_code}) - {response.text}")
                break

        except requests.exceptions.Timeout:
            print(f"⏳ TIMEOUT: SEC API did not respond. Retrying in {RETRY_DELAY} sec (Attempt {attempt}/{MAX_RETRIES})...")
            time.sleep(RETRY_DELAY)

        except requests.exceptions.RequestException as e:
            print(f"❌ ERROR: API request failed ({str(e)}). Retrying in {RETRY_DELAY} sec (Attempt {attempt}/{MAX_RETRIES})...")
            time.sleep(RETRY_DELAY)

    print("🚨 FINAL ERROR: SEC API failed after multiple attempts. Please try again later.")
    return None  # Return None if all attempts fail

# 🔹 STEP 2: FIND XBRL URL
def find_xbrl_url(index_url):
    """Finds the XBRL file URL from an SEC index.json."""
    time.sleep(REQUEST_DELAY)

    response = fetch_with_retries(index_url)
    if not response:
        return None

    try:
        if "directory" in response and "item" in response["directory"]:
            for file in response["directory"]["item"]:
                if file["name"].endswith(".xml") and "htm.xml" in file["name"]:
                    return index_url.replace("index.json", file["name"])
    except json.JSONDecodeError:
        return None

    return None  # No XBRL file found

# 🔹 STEP 3: EXTRACT FINANCIAL DATA FROM XBRL
def extract_summary(xbrl_url):
    """Parses XBRL data to extract key financial metrics."""
    if not xbrl_url:
        print("❌ ERROR: Invalid XBRL URL")
        return {}

    time.sleep(REQUEST_DELAY)
    response = requests.get(xbrl_url, headers=HEADERS, timeout=TIMEOUT)

    if response.status_code != 200:
        print("❌ ERROR: Failed to fetch XBRL file")
        return {}

    try:
        root = etree.fromstring(response.content)
    except etree.XMLSyntaxError:
        print("❌ ERROR: XML parsing failed")
        return {}

    namespaces = {k if k else "default": v for k, v in root.nsmap.items()}  

    # ✅ **Key Mappings**
    key_mappings = {
        "Revenue": [
            "Revenue", "TotalRevenue", "SalesRevenueNet",
            "OperatingRevenue", "TotalNetSales",
            "RevenueFromContractWithCustomerExcludingAssessedTax"
        ],
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
        ],
        "Inventory": ["InventoryNet", "Inventories"],
        "AccountsReceivable": ["AccountsReceivableNet", "ReceivablesNetCurrent"],
        "CapitalExpenditures": [
            "PaymentsToAcquirePropertyPlantAndEquipment",
            "PurchaseOfPropertyPlantAndEquipment"
        ],
        "InterestExpense": [
            "InterestExpense", "InterestAndDebtExpense", "FinanceExpense"
        ],
        "IncomeTaxExpense": ["IncomeTaxExpenseBenefit", "ProvisionForIncomeTaxes"]
    }

    # ✅ Extract Key Financials
    financials = {}
    for key, tags in key_mappings.items():
        for tag in tags:
            values = root.xpath(f"//*[local-name()='{tag}']/text()", namespaces=namespaces)
            if values:
                financials[key] = values[-1].replace(",", "")
                break  # ✅ Stop at first match

    # ✅ Compute Debt & Extract Maturities
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

    # ✅ Extract Debt Maturities (Breakdown by Year)
    debt_maturities = {}
    maturity_tags = [
        "LongTermDebtMaturitiesRepaymentsOfPrincipalRemainderOfFiscalYear",
        "LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths",
        "LongTermDebtMaturitiesRepaymentsOfPrincipalYearOne",
        "LongTermDebtMaturitiesRepaymentsOfPrincipalYearTwo",
        "LongTermDebtMaturitiesRepaymentsOfPrincipalYearThree",
        "LongTermDebtMaturitiesRepaymentsOfPrincipalYearFour",
        "LongTermDebtMaturitiesRepaymentsOfPrincipalYearFive",
        "LongTermDebtMaturitiesRepaymentsOfPrincipalAfterFiveYears"
    ]

    for tag in maturity_tags:
        values = root.xpath(f"//*[local-name()='{tag}']/text()", namespaces=namespaces)
        if values:
            debt_maturities[tag] = values[0].replace(",", "")

    # ✅ Final Output
    financials["Debt"] = str(int(total_debt)) if total_debt > 0 else "N/A"
    financials["DebtMaturities"] = debt_maturities

    return financials
