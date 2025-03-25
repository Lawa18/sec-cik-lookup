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
    """Parses XBRL data to extract key financial metrics with improved accuracy."""
    
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

    # ✅ **Fully Restored `key_mappings` (Removed Total Liabilities, Added Equity)**
    key_mappings = {
        "Revenue": [
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "Revenues",
            "RevenueRecognitionPolicyTextBlock",
            "DisaggregationOfRevenueTableTextBlock",
            "ReconciliationOfRevenueFromSegmentsToConsolidatedTextBlock",
            "ScheduleOfRevenueFromExternalCustomersAttributedToForeignCountriesByGeographicAreaTextBlock",
            "SalesRevenueNet",
            "Revenue"
        ],
        "NetIncome": [
            "NetIncomeLoss",
            "IncomeLossFromContinuingOperationsBeforeIncomeTaxesDomestic",
            "OperatingIncomeLoss",
            "NetIncomeLossAvailableToCommonStockholdersDiluted"
        ],
        "TotalAssets": [
            "Assets",
            "TotalAssets",
            "AssetsFairValueDisclosure",
            "GrossCustomerFinancingAssets",
            "BalanceSheetAbstract",
            "StatementOfFinancialPositionAbstract"
        ],
        "OperatingCashFlow": [
            "NetCashProvidedByUsedInOperatingActivities",
            "CashCashEquivalentsAndShortTermInvestments",
            "OperatingActivitiesCashFlowsAbstract",
            "CashGeneratedByOperatingActivities"
        ],
        "CurrentAssets": [
            "AssetsCurrent",
            "CurrentPortionOfFinancingReceivablesNet",
            "ContractWithCustomerReceivableBeforeAllowanceForCreditLossCurrent",
            "CurrentAssets"
        ],
        "CurrentLiabilities": [
            "LiabilitiesCurrent",
            "AccountsPayableCurrent",
            "OtherAccruedLiabilitiesCurrent",
            "CurrentLiabilities"
        ],
        "CashPosition": [
            "CashAndCashEquivalentsAtCarryingValue",
            "CashAndCashEquivalents",
            "RestrictedCashAndCashEquivalents",
            "CashAndShortTermInvestments"
        ],
        "Inventory": [
            "InventoryNet",
            "ScheduleOfInventoryCurrentTableTextBlock",
            "InventoryForLongTermContractsOrPrograms",
            "Inventories"
        ],
        "AccountsReceivable": [
            "AccountsReceivableNet",
            "AccountsReceivableGrossCurrent",
            "UnbilledContractsReceivable",
            "ReceivablesNetCurrent"
        ],
        "CapitalExpenditures": [
            "PaymentsToAcquirePropertyPlantAndEquipment",
            "PropertyPlantAndEquipmentTextBlock",
            "PropertyPlantAndEquipmentAdditionsNonCash"
        ],
        "InterestExpense": [
            "InterestExpense",
            "InterestAndDebtExpense",
            "InterestPaid"
        ],
        "IncomeTaxExpense": [
            "IncomeTaxExpenseBenefit",
            "DeferredIncomeTaxExpenseBenefit",
            "EffectiveIncomeTaxRateContinuingOperations"
        ],
        "Debt": [
            "LongTermDebt",
            "LongTermDebtNoncurrent",
            "DebtInstrumentCarryingAmount",
            "LongTermDebtAndCapitalLeaseObligations",
            "DebtDisclosureTextBlock",
            "DebtCurrent",
            "NotesPayable",
            "DebtObligations",
            "DebtInstruments"
        ],
        "Equity": [
            "StockholdersEquity",
            "Equity",
            "CommonStockValue",
            "RetainedEarningsAccumulatedDeficit"
        ]
    }

    financials = {}

    # ✅ **Step 1: Identify Latest Reporting Date**
    reporting_dates = root.xpath("//context[period/endDate]/period/endDate/text()", namespaces=namespaces)
    if reporting_dates:
        latest_reporting_date = max(reporting_dates)  # Get the latest date

    # ✅ **Step 2: Extract Key Financials Only for Latest Reporting Date**
    for key, tags in key_mappings.items():
        extracted_values = []
        for tag in tags:
            # Find values associated with the latest reporting date
            values = root.xpath(f"//*[local-name()='{tag}'][../contextRef[contains(text(), '{latest_reporting_date}')]]/text()", namespaces=namespaces)
            extracted_values.extend(values)

        # ✅ Convert to numerical format
        if extracted_values:
            try:
                financials[key] = max([float(v.replace(",", "")) for v in extracted_values if v.replace(",", "").replace(".", "").isdigit()])
            except ValueError:
                financials[key] = "N/A"

    # ✅ **Step 3: Compute Debt More Accurately**
    total_debt = 0
    for tag in key_mappings["Debt"]:
        values = root.xpath(f"//*[local-name()='{tag}'][../contextRef[contains(text(), '{latest_reporting_date}')]]/text()", namespaces=namespaces)
        if values:
            try:
                total_debt += float(values[0].replace(",", ""))
            except ValueError:
                pass

    financials["Debt"] = str(int(total_debt)) if total_debt > 0 else "N/A"

    # ✅ **Step 4: Compute Correct Cash Position (Cash + Short-Term Investments)**
    cash_values = []
    for tag in ["CashAndCashEquivalentsAtCarryingValue", "ShortTermInvestments"]:
        values = root.xpath(f"//*[local-name()='{tag}'][../contextRef[contains(text(), '{latest_reporting_date}')]]/text()", namespaces=namespaces)
        cash_values.extend(values)

    if cash_values:
        try:
            total_cash = sum(float(v.replace(",", "")) for v in cash_values if v.replace(",", "").replace(".", "").isdigit())
            financials["CashPosition"] = str(int(total_cash))
        except ValueError:
            financials["CashPosition"] = "N/A"

    return financials
