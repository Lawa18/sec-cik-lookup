def extract_line_items_from_ixbrl(htm_text, fallback_tags):
    from bs4 import BeautifulSoup
    import warnings
    from bs4 import XMLParsedAsHTMLWarning

    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
    soup = BeautifulSoup(htm_text, "lxml")

    extracted = {}

    for metric, tags in fallback_tags.items():
        found = False
        for full_tag in tags:
            tag_name = full_tag.split(":")[-1]
            candidates = soup.find_all(attrs={"name": tag_name})
            for tag in candidates:
                if tag.string and tag.string.strip():
                    try:
                        extracted[metric] = float(tag.string.replace(",", "").replace("(", "-").replace(")", ""))
                    except:
                        extracted[metric] = tag.string.strip()
                    found = True
                    break
            if found:
                break
        if not found:
            extracted[metric] = "Missing tag"

    print(f"🧠 Extracted {len(extracted)} fields from iXBRL.")
    return extracted
