from datetime import datetime
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class LLM:
    trade_context = {}  # Tracks open positions: {symbol: {contract_type, expiry, strike, entry, quantity}}
    last_reset_date = datetime.now().date()

    def __init__(self, model_name: str = "deepseek-chat"):
        self.model_name = model_name
        self.client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com"
        )
        self.system_prompt = (
            "You are the best trader and an expert in quantitative options trading."
            " You will be given a prompt containing any kind of message — it could be a direct trade alert, news update, or a speculative idea."
            " Your task is to carefully analyze the message and infer whether the most appropriate action is one of the following:"
            " (1) BUY — if the message contains a clear, actionable trade entry signal, covering means covering your short so it's long;"
            " (2) SELL — if the message recommends trimming, scaled, trim, taking profit, exiting a position, or closing a trade"
            " (3) SPECULATE — if the message is saying im looking at, general commentary, analysis, or news that suggests watching but not yet acting."
            " The action can only be one of BUY, SELL, and SPECULATE. Things like taking profit and trimming mean SELL, grabbing means buying."
            " you can only return SELL if your current holding of this quantity is strictly larger than 0."
            " If relevant, extract the following details from the message: symbol, contract_type (call or put), expiry date (e.g. 6/06), strike price (an integer), entry price, quantity."
            " Quantity for BUY is always two unless specified. Quantity for SELL is always one."
            " the expiry should be in the format YYYYMMDD. YYYY is always 2025 unless specified."
            " Then return ONLY a JSON with all the following fields: symbol:..., contract_type:..., expiry:..., strike:..., action:..., quantity:... "
            " If some fields are not found, fill them with null. be very very concise and return ONLY a JSON with no extra words."
        )

    def reset_context_if_needed(self):
        current_date = datetime.now().date()
        if current_date != self.last_reset_date:
            print(f"[Reset] Clearing trade context for new day: {current_date}")
            self.trade_context.clear()
            self.last_reset_date = current_date

    def validate_sell_action(self, symbol: str):
        """Check if SELL is allowed (position exists)."""
        return symbol in self.trade_context

    def update_trade_context(self, trade_data: dict):
        """Update context after BUY/SELL actions."""
        symbol = trade_data["symbol"]

        if trade_data["action"] == "BUY":
            # For BUY actions, add or update the position
            if symbol in self.trade_context:
                # If position exists, increase quantity
                self.trade_context[symbol]["quantity"] += trade_data.get("quantity", 2)
            else:
                # New position
                self.trade_context[symbol] = {
                    "contract_type": trade_data["contract_type"],
                    "expiry": trade_data["expiry"],
                    "strike": trade_data["strike"],
                    "entry": trade_data["entry"],
                    "quantity": trade_data.get("quantity", 2)  # Default 2 for BUY
                }

        elif trade_data["action"] == "SELL":
            # For SELL actions, decrement quantity
            if symbol in self.trade_context:
                current_qty = self.trade_context[symbol]["quantity"]
                sell_qty = trade_data.get("quantity", 1)  # Default 1 for SELL

                if sell_qty >= current_qty:
                    # Remove if selling all or more than we have
                    self.trade_context.pop(symbol)
                else:
                    # Decrement quantity
                    self.trade_context[symbol]["quantity"] -= sell_qty

    def prompt(self, user_prompt: str) -> dict:
        self.reset_context_if_needed()

        # Inject context if symbol exists
        for symbol in self.trade_context:
            if symbol.lower() in user_prompt.lower():
                context = self.trade_context[symbol]
                user_prompt = (
                        f"Current position: {symbol} {context['contract_type']} "
                        f"exp {context['expiry']} strike {context['strike']}. "
                        + user_prompt
                )
                break

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=512
        )

        try:
            output = json.loads(response.choices[0].message.content.strip())

            # Validate SELL actions
            if output.get("action") == "SELL" and not self.validate_sell_action(output["symbol"]):
                return {"error": f"Cannot SELL - no position for {output['symbol']}"}

            # Update context if valid BUY/SELL
            if output["action"] in ("BUY", "SELL"):
                self.update_trade_context(output)

            return output

        except json.JSONDecodeError as e:
            return {
                "error": "Invalid JSON response",
                "raw_output": response.choices[0].message.content,
                "exception": str(e)
            }


# Example Usage
if __name__ == "__main__":
    llm = LLM()