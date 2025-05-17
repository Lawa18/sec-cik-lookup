from bs4 import BeautifulSoup

def extract_line_items_from_ixbrl(htm_text, fallback_tags):
    soup = BeautifulSoup(htm_text, "lxml")
    extracted = {}

    try:
        elements = soup.find_all(["ix:nonfraction", "ix:nonnumeric"], limit=10000)

        for metric, tags in fallback_tags.items():
            found = False
            for tag_name in tags:
                for el in elements:
                    name = el.get("name")
                    if name and tag_name.lower() in name.lower():
                        try:
                            extracted[metric] = float(el.text.replace(",", "").replace("(", "-").replace(")", ""))
                        except:
                            extracted[metric] = el.text.strip()
                        found = True
                        break
                if found:
                    break
            if not found:
                extracted[metric] = "Missing tag"

    except Exception as e:
        print(f"❌ iXBRL Parse error: {e}")

    print(f"📊 Extracted {len(extracted)} iXBRL metrics.")
    return extracted
