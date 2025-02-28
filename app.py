@app.route("/financials", methods=["GET"])
def get_financials():
    query = request.args.get("query", "").strip().lower()

    if not query:
        return jsonify({"error": "Query parameter is required."}), 400

    # Load both datasets (Fix: Use cik_names.json instead of cik_titles.json)
    ticker_dict = load_json("cik_tickers.json")
    company_dict = load_json("cik_names.json")  # Corrected file name

    # Convert keys to lowercase for case-insensitive search
    ticker_dict = {key.lower(): value for key, value in ticker_dict.items()}
    company_dict = {key.lower(): value for key, value in company_dict.items()}

    # Lookup by exact ticker or company name
    cik = ticker_dict.get(query) or company_dict.get(query)

    # Partial match (if no exact match)
    if not cik:
        for name, cik_value in company_dict.items():
            if query in name:
                cik = cik_value
                break

    if not cik:
        return jsonify({"error": "CIK not found."}), 404

    return jsonify({"cik": cik})
