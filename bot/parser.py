from datetime import datetime
from llm import LLM

llm = LLM()

def parse_message(text):
    try:
        response = llm.prompt(text)
        trade = {}
        for line in response.splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                key, val = key.strip().lower(), val.strip()
                if key in ["strike", "price", "entry"]:
                    trade["entry"] = float(val)
                elif key == "quantity":
                    trade["quantity"] = int(val)
                elif key == "symbol":
                    trade["symbol"] = val.upper()
                elif key == "expiry":
                    trade["expiry"] = val
                elif key == "contract_type":
                    trade["contract_type"] = val.upper()
                elif key == "action":
                    trade["action"] = val.upper()
        trade.setdefault("quantity", 1)
        trade.setdefault("action", "BUY")
        trade["timestamp"] = datetime.utcnow().isoformat()
        trade["source"] = text
        return [trade] if "symbol" in trade and "entry" in trade else []
    except Exception as e:
        print(f"[x] LLM parsing error: {e}")
        return []
