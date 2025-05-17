from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import warnings

def extract_line_items_from_ixbrl(htm_text, fallback_tags):
    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
    soup = BeautifulSoup(htm_text, "lxml")  # Use lxml to avoid HTMLParser crash

    extracted = {}

    for metric, tag_names in fallback_tags.items():
        found = False
        for tag in soup.find_all(True):  # Iterate all tags
            if tag.name and "non" in tag.name.lower():  # covers ix:nonFraction, ix:nonNumeric
                name_attr = tag.get("name", "").lower()
                for fallback_tag in tag_names:
                    if fallback_tag.lower() in name_attr:
                        value = tag.get_text(strip=True).replace(",", "").replace("(", "-").replace(")", "")
                        try:
                            extracted[metric] = float(value)
                        except:
                            extracted[metric] = value
                        found = True
                        break
            if found:
                break
        if not found:
            extracted[metric] = "Missing tag"

    print(f"📊 Extracted {len(extracted)} iXBRL metrics.")
    return extracted
