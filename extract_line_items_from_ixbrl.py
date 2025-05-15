from bs4 import BeautifulSoup
import warnings
from bs4 import XMLParsedAsHTMLWarning

def extract_line_items_from_ixbrl(htm_text, fallback_tags):
    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
    soup = BeautifulSoup(htm_text, "lxml")

    extracted = {}

    for metric, tags in fallback_tags.items():
        found = False
        for tag in tags:
            tag_name = tag.split(":")[-1]
            # Match any tag with matching name attribute (ignores prefix issues)
            candidates = soup.find_all(attrs={"name": tag_name})
            for el in candidates:
                text = el.get_text(strip=True)
                if text:
                    try:
                        extracted[metric] = float(text.replace(",", "").replace("(", "-").replace(")", ""))
                    except:
                        extracted[metric] = text
                    found = True
                    break
            if found:
                break
        if not found:
            extracted[metric] = "Missing tag"

    print(f"🌐 Extracted {len(extracted)} iXBRL metrics.")
    return extracted
