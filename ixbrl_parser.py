from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import warnings

def parse_ixbrl_metrics(htm_text, fallback_tags):
    # should start with this check
    if not htm_text or len(htm_text) < 10000:
        print("❌ Invalid or too-small iXBRL HTML.")
        return {"error": "Downloaded iXBRL file is invalid or too small."}

    from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
    import warnings
    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

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
        for tag in soup.find_all(name=lambda x: x and "non" in x.lower()):
            name_attr = tag.get("name", "").lower()
            for fallback_tag in tag_names:
                if fallback_tag.lower() in name_attr:
                    text = tag.get_text(strip=True)
                    text = text.replace(",", "").replace("(", "-").replace(")", "")
                    try:
                        extracted[metric] = float(text)
                    except:
                        extracted[metric] = text
                    found = True
                    break
            if found:
                break
        if not found:
            extracted[metric] = "Missing tag"

    print(f"📊 Extracted {len(extracted)} iXBRL metrics.")
    return extracted
