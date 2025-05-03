import requests
from xbrl_parser import find_xbrl_url, extract_summary  # ✅ Import once at the top

def fetch_sec_data(cik):
    """Fetch latest and historical financials from SEC API."""
    sec_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    headers = {
        "User-Agent": "Lars Wallin lars.e.wallin@gmail.com",
        "Accept": "application/json"
    }
    
import time
import os

# Basic request headers to SEC
HEADERS = {
    'User-Agent': 'Lars Wallin (lars.e.wallin@gmail.com)',
    'Accept-Encoding': 'gzip, deflate',
    'Accept': '*/*',
    'Connection': 'keep-alive'
}

SEC_API_BASE = 'https://data.sec.gov'


def safe_get(url, headers=HEADERS, retries=3, delay=1):
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(delay)
    raise Exception(f"Failed to fetch URL after {retries} attempts: {url}")


def get_company_submissions(cik):
    cik = cik.zfill(10)
    url = f"{SEC_API_BASE}/submissions/CIK{cik}.json"
    return safe_get(url).json()


def get_filing_index(cik, accession):
    acc_no_no_hyphens = accession.replace('-', '')
    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_no_no_hyphens}/index.json"
try:
        sec_response = requests.get(sec_url, headers=headers, timeout=10)  # ✅ Added timeout for reliability
        sec_response.raise_for_status()  # ✅ Raises an error for bad responses (4xx, 5xx)
    except requests.RequestException as e:
        print(f"❌ ERROR: Failed to fetch SEC data for CIK {cik}: {e}")
        return {}  # ✅ Return empty dictionary instead of None to prevent crashes

    return sec_response.json()

def get_sec_financials(cik):
    """Extracts the last 5 years of annual and last 4 quarters of financials from SEC filings."""
    data = fetch_sec_data(cik)
    if not data:
        return {
            "company": "Unknown",
            "cik": cik,
            "historical_annuals": [],
            "historical_quarters": []
        }

    filings = data.get("filings", {}).get("recent", {})
    forms = filings.get("form", [])
    filing_dates = filings.get("filingDate", [])
    accession_numbers = filings.get("accessionNumber", [])
    primary_documents = filings.get("primaryDocument", [])

    historical_annuals = []
    historical_quarters = []
    
    seen_years = set()
    seen_quarters = 0

    for i, form in enumerate(forms):
        # ✅ Prevent index errors
        if i >= len(filing_dates) or i >= len(accession_numbers) or i >= len(primary_documents):
            continue

        filing_year = filing_dates[i][:4] if filing_dates[i] else "N/A"

        if form in ["10-K", "20-F"] and filing_year not in seen_years and len(seen_years) < 5:
            seen_years.add(filing_year)
        elif form in ["10-Q", "6-K"] and seen_quarters < 4:
            seen_quarters += 1
        else:
            continue  # ✅ Skip if we already have enough filings

        accession_number = accession_numbers[i]
        if not accession_number:
            continue

        index_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_number.replace('-', '')}/index.json"
        xbrl_url = find_xbrl_url(index_url)
        financials = extract_summary(xbrl_url) if xbrl_url else {}

        filing_data = {
            "formType": form,
            "filingDate": filing_dates[i],
            "filingUrl": f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_number.replace('-', '')}/{primary_documents[i]}",
            "xbrlUrl": xbrl_url if xbrl_url else "XBRL file not found.",
            "financials": financials
        }

        if form in ["10-K", "20-F"]:
            historical_annuals.append(filing_data)
        elif form in ["10-Q", "6-K"]:
            historical_quarters.append(filing_data)

    # ✅ Filter out 6-Ks with no financial data
    historical_quarters = [
        filing for filing in historical_quarters 
        if filing.get("financials") and isinstance(filing["financials"], dict) and any(value != "N/A" for value in filing["financials"].values())
        return safe_get(url).json()
    except Exception:
        hyphenated_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/index.json"
        return safe_get(hyphenated_url).json()


def find_instance_xbrl_url(index_data, cik, accession):
    acc_no = accession.replace('-', '')
    for file in index_data.get("directory", {}).get("item", []):
        print(f"🔍 Inspecting file: {file['name']}")
        filename = file['name'].lower()
        if filename.endswith(".xml") and '_def' not in filename and '_pre' not in filename and '_lab' not in filename and '_cal' not in filename:
            return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_no}/{file['name']}"
    return None


def get_recent_filings(cik, k_count=2, q_count=4):
    cik = cik.zfill(10)
    url = f"{SEC_API_BASE}/submissions/CIK{cik}.json"
    data = safe_get(url).json().get('filings', {}).get('recent', {})
    forms = data.get('form', [])
    accessions = data.get('accessionNumber', [])
    filing_dates = data.get('filingDate', [])

    all_filings = [
        {"form": form, "accession": acc, "date": date}
        for form, acc, date in zip(forms, accessions, filing_dates)
        if form in ['10-K', '10-Q']
]

    return {
        "company": data.get("name", "Unknown"),
        "cik": cik,
        "historical_annuals": historical_annuals,
        "historical_quarters": historical_quarters
    }
    all_filings.sort(key=lambda x: x['date'], reverse=True)

    results = []
    k_fetched = 0
    q_fetched = 0

    for f in all_filings:
        print(f"📄 Found {f['form']} filing: {f['accession']} dated {f['date']}")
        if f["form"] == "10-K" and k_fetched < k_count:
            results.append(("10-K", f["accession"], f["date"]))
            k_fetched += 1
        elif f["form"] == "10-Q" and q_fetched < q_count:
            results.append(("10-Q", f["accession"], f["date"]))
            q_fetched += 1

        if k_fetched >= k_count and q_fetched >= q_count:
            break

    return results


def download_multiple_xbrl(cik, save_dir='xbrl_files'):
    os.makedirs(save_dir, exist_ok=True)
    filings = get_recent_filings(cik)

    downloaded_files = []

    for form_type, acc, date in filings:
        try:
            print(f"📥 Processing {form_type} for {cik} — Accession: {acc} — Date: {date}")
            index_data = get_filing_index(cik, acc)
            xbrl_url = find_instance_xbrl_url(index_data, cik, acc)
            if xbrl_url:
                response = safe_get(xbrl_url)
                filename = f"{cik}_{form_type}_{date}.xml"
                filepath = os.path.join(save_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print(f"✅ Downloaded {form_type} ({date}) to: {filepath}")
                downloaded_files.append(filepath)
            else:
                print(f"⚠️ No XBRL instance found for {form_type} {date}")
        except Exception as e:
            print(f"❌ Error fetching {form_type} for {cik}: {e}")

    return downloaded_files


if __name__ == "__main__":
    cik = "0001543151"  # Uber example
    download_multiple_xbrl(cik)
