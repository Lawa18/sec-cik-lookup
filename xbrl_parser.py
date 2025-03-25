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

def extract_summary(xbrl_url):
    """Extracts key financial metrics ensuring correct Net Income, Equity, and Cash Position"""

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

    # ✅ **Key Mappings for Financial Metrics**
    key_mappings = {
        "Revenue": [
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "Revenues",
            "SalesRevenueNet",
            "Revenue"
        ],
        "NetIncome": [  # ✅ FIXED: Only extracts the latest Net Income
            "NetIncomeLoss",
            "NetIncomeLossAvailableToCommonStockholdersDiluted",
            "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"
        ],
        "TotalAssets": [
            "Assets",
            "TotalAssets",
            "AssetsFairValueDisclosure",
            "GrossCustomerFinancingAssets"
        ],
        "OperatingCashFlow": [
            "NetCashProvidedByUsedInOperatingActivities",
            "OperatingActivitiesCashFlowsAbstract",
            "CashGeneratedByOperatingActivities"
        ],
        "CurrentAssets": [
            "AssetsCurrent",
            "CurrentPortionOfFinancingReceivablesNet",
            "ContractWithCustomerReceivableBeforeAllowanceForCreditLossCurrent"
        ],
        "CurrentLiabilities": [
            "LiabilitiesCurrent",
            "AccountsPayableCurrent",
            "OtherAccruedLiabilitiesCurrent"
        ],
        "CashPosition": [  # ✅ FIXED: Cash + Short-Term Investments
            "CashAndCashEquivalentsAtCarryingValue",
            "CashAndCashEquivalents",
            "RestrictedCashAndCashEquivalents",
            "CashAndShortTermInvestments",
            "ShortTermInvestments"
        ],
        "Equity": [  # ✅ FIXED: Ensures correct "Total Stockholders' Equity"
            "StockholdersEquity",
            "TotalStockholdersEquity",
            "CommonStockValue",
            "RetainedEarningsAccumulatedDeficit",
            "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
            "TotalEquity"
        ],
        "Debt": [  # ✅ FIXED: More accurate Debt calculation
            "LongTermDebt",
            "LongTermDebtNoncurrent",
            "DebtInstrumentCarryingAmount",
            "LongTermDebtAndCapitalLeaseObligations",
            "DebtCurrent",
            "NotesPayable"
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
