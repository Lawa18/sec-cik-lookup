import requests
from lxml import etree

def find_xbrl_url(index_url):
    """Fetches SEC index.json and finds the correct XBRL file for financial data."""
    headers = {"User-Agent": "Lars Wallin lars.e.wallin@gmail.com"}
    response = requests.get(index_url, headers=headers)

    if response.status_code != 200:
        print(f"ERROR: Failed to fetch index.json. Status: {response.status_code}")
        return None

    try:
        index_data = response.json()
        xbrl_file = None

        # ✅ Prioritize MAIN financial statement XBRL files
        for file in index_data["directory"]["item"]:
            name = file["name"].lower()
            if name.endswith(("_htm.xml", "_full.xml")):
                xbrl_file = f"{index_url.rsplit('/', 1)[0]}/{file['name']}"
                break  

        return xbrl_file

    except Exception as e:
        print(f"ERROR: Could not parse SEC index.json: {e}")
        return None

import requests
from lxml import etree

def extract_summary(xbrl_url):
    """Extracts financial data from XBRL SEC filing with better namespace handling."""
    if not xbrl_url:
        return "No XBRL file found."

    headers = {"User-Agent": "Lars Wallin lars.e.wallin@gmail.com"}
    response = requests.get(xbrl_url, headers=headers)

    if response.status_code != 200:
        return f"Error fetching XBRL report. Status: {response.status_code}"

    try:
        parser = etree.XMLParser(recover=True)
        tree = etree.fromstring(response.content, parser=parser)

        # ✅ Debug: Print XBRL Namespace Map
        namespaces = tree.nsmap
        print("🔍 DEBUG: Extracted Namespaces from XBRL:", namespaces)

        # ✅ Debug: Print First 1000 Characters of XBRL File
        print(f"🔍 DEBUG: XBRL File Content (First 1000 chars):\n{response.text[:1000]}")

        # 🛠 Ensure correct namespace handling
        ns = {"x": namespaces[None]} if None in namespaces else {}
        print("✅ DEBUG: Namespace used in queries:", ns)

        # ✅ Extract Key Financial Data with Namespace Fix
        financials = {
            "Revenue": extract_xbrl_value(tree, "Revenues", ns),
            "NetIncome": extract_xbrl_value(tree, "NetIncomeLoss", ns),
            "TotalAssets": extract_xbrl_value(tree, "Assets", ns),
            "TotalLiabilities": extract_xbrl_value(tree, "Liabilities", ns),
            "OperatingCashFlow": extract_xbrl_value(tree, "NetCashProvidedByUsedInOperatingActivities", ns),
            "CurrentAssets": extract_xbrl_value(tree, "AssetsCurrent", ns),
            "CurrentLiabilities": extract_xbrl_value(tree, "LiabilitiesCurrent", ns),
            "Debt": extract_xbrl_value(tree, "LongTermDebtNoncurrent", ns)
        }

        print("✅ DEBUG: Extracted Financial Data:", financials)

        return financials

    except etree.XMLSyntaxError:
        return "Error: XML Syntax Error - File may be corrupted."

    except Exception as e:
        return f"Error extracting financial data: {str(e)}"

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
