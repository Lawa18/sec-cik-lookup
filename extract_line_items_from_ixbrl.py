from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import warnings

def extract_line_items_from_ixbrl(htm_text, fallback_tags):
    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
    soup = BeautifulSoup(htm_text, "lxml", from_encoding="utf-8")

    extracted = {}

    for metric, tag_names in fallback_tags.items():
        found = False
        for tag in soup.find_all(True):
            if tag.name and "non" in tag.name.lower():  # catches ix:nonFraction/nonnumeric
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
