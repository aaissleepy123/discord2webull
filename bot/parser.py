from datetime import datetime
from llmopenai import LLM
import json

llm = LLM()

def parse_message(text):
    try:
        response = llm.prompt(text)

        # Parse JSON string from LLM into dict
        trade = dict(
            (k.strip(), v.strip()) for k, v in
            (field.split(":", 1) for field in response.split(", ") if ":" in field)
        )

        # Required fields
        required = ["symbol", "contract_type", "expiry", "strike", "action", "quantity"]
        if not all(field in trade for field in required):
            print(f"[!] Missing fields in trade: {trade}")
            return []

        # Normalize with stripping
        trade["symbol"] = trade["symbol"].strip().upper()
        trade["contract_type"] = trade["contract_type"].strip().upper()[0]  # safer: could add check
        trade["expiry"] = trade["expiry"].strip()
        trade["strike"] = float(trade["strike"].strip())
        trade["quantity"] = int(trade["quantity"].strip())
        trade["action"] = trade["action"].strip().upper()

        # Validate contract_type
        if trade["contract_type"] not in {"C", "P"}:
            print(f"[!] Invalid contract_type: {trade['contract_type']}")
            return []

        # Validate expiry (simple YYYYMMDD check)
        if not (trade["expiry"].isdigit() and len(trade["expiry"]) == 8):
            print(f"[!] Invalid expiry: {trade['expiry']}")
            return []
        expiry_date = trade["expiry"]
        if expiry_date.startswith("2024"):
            # Replace 2024 with 2025 while keeping month/day the same
            corrected_expiry = "2025" + expiry_date[4:]
            trade["expiry"] = corrected_expiry

        # Add timestamp + source
        trade["timestamp"] = datetime.utcnow().isoformat()
        trade["source"] = text

        return [trade]
    except Exception as e:
        print(f"[x] LLM parsing error: {e}")
        return []