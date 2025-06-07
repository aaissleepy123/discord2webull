from datetime import datetime
from llmopenai import LLM
import json

llm = LLM()

def parse_message(text):
    try:
        response = llm.prompt(text)

        # Parse JSON string from LLM into dict
        trade = json.loads(response)

        # Sanity check for required fields
        required = ["symbol", "contract_type", "expiry", "strike", "action", "quantity"]
        if not all(field in trade for field in required):
            print(f"[!] Missing fields in trade: {trade}")
            return []

        # Normalize field types and values
        trade["symbol"] = trade["symbol"].upper()
        trade["contract_type"] = trade["contract_type"].upper()[0]  # 'C' or 'P'
        trade["expiry"] = str(trade["expiry"])
        trade["strike"] = float(trade["strike"])
        trade["entry"] = float(trade["entry"])
        trade["quantity"] = int(trade["quantity"])
        trade["action"] = trade["action"].upper()

        # Add timestamp and source
        trade["timestamp"] = datetime.utcnow().isoformat()
        trade["source"] = text

        return [trade]

    except Exception as e:
        print(f"[x] LLM parsing error: {e}")
        return []
