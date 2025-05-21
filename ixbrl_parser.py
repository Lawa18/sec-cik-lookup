print("🚀 Dummy change to force redeploy")

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import warnings

def parse_ixbrl_and_extract(htm_text, fallback_tags):
    # Suppress warnings for iXBRL being parsed as HTML
    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

    if not htm_text or len(htm_text) < 10000:
        print("❌ Invalid or too-small iXBRL HTML.")
        return {"error": "Downloaded iXBRL file is invalid or too small."}

    try:
        print("🔍 Starting BeautifulSoup parse (html5lib)")
        soup = BeautifulSoup(htm_text, "html5lib")
        print("✅ Soup parsed successfully")
    except Exception as e:
        print(f"❌ Soup parse failed: {e}")
        return {"error": f"Soup parse failed: {str(e)}"}

    extracted = {}

    for metric, tag_names in fallback_tags.items():
        found = False
        # Look for any element that might be a numeric/non-numeric ixbrl tag
        for tag in soup.find_all(name=lambda x: x and "non" in x.lower()):
            name_attr = tag.get("name", "").lower()
            if not name_attr:
                continue

            for fallback_tag in tag_names:
                if fallback_tag.lower() in name_attr:
                    text = tag.get_text(strip=True)
                    text = text.replace(",", "").replace("(", "-").replace(")", "")
                    try:
                        extracted[metric] = float(text)
                    except ValueError:
                        extracted[metric] = text
                    found = True
                    break

            if found:
                break

        if not found:
            extracted[metric] = "Missing tag"

    print(f"📊 Extracted {len(extracted)} iXBRL metrics.")
    return extracted
