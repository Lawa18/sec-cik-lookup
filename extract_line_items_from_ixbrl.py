# extract_line_items_from_ixbrl.py

from bs4 import BeautifulSoup
import warnings
from bs4 import XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

def extract_line_items_from_ixbrl(htm_text, fallback_tags):
    soup = BeautifulSoup(htm_text, "lxml")

    extracted = {}

    for metric, tags in fallback_tags.items():
        found = False
        for full_tag in tags:
            tag_name = full_tag.split(":")[-1]
            try:
                # ✅ Safe generator catch block
                candidates = soup.find_all(attrs={"name": tag_name}, limit=1000)
                candidates = list(candidates)  # materialize to avoid generator crashes
            except Exception as e:
                print(f"⚠️ iXBRL tag search failed for '{tag_name}': {e}")
                continue

            for tag in candidates:
                try:
                    if tag.string and tag.string.strip():
                        text = tag.string.strip()
                        try:
                            extracted[metric] = float(text.replace(",", "").replace("(", "-").replace(")", ""))
                        except:
                            extracted[metric] = text
                        found = True
                        break
                except Exception as inner_e:
                    print(f"⚠️ Error parsing tag for {metric}: {inner_e}")
            if found:
                break
        if not found:
            extracted[metric] = "Missing tag"

    print(f"🧠 Extracted {len(extracted)} fields from iXBRL.")
    return extracted
