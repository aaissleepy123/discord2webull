import openai
from httpx import HTTPStatusError
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
import os
from datetime import datetime
import time


class LLM:
    trade_context = {}  # Example: { "META": {contract_type: ..., ..., position: 2} }
    last_reset_date = datetime.now().date()

    def __init__(self, model_name: str = "gpt-4o"):
        self.model_name = model_name
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        self.system_prompt = (
            "You are the best trader and an expert in quantitative options trading."
            " You will be given a prompt containing any kind of message — it could be a direct trade alert, news update, or a speculative idea."
            " Your task is to carefully analyze the message and infer whether the most appropriate action is one of the following:"
            " (1) BUY — if the message contains a clear, actionable trade entry signal, covering means covering your short so it's long;"
            " (2) SELL — if the message recommends trimming, scaled, trim, taking profit, exiting a position, or closing a trade"
            " (3) SPECULATE — if the message is saying im looking at, general commentary, analysis, or news that suggests watching but not yet acting."
            " The action can only be one of BUY, SELL, and SPECULATE. Things like taking profit and trimming mean SELL, grabbing means buying."
            " you can only return SELL if your current holding of this quantity is strictly larger than 0."
            " If relevant, extract the following details from the message: symbol, contract_type (call or put), expiry date (e.g. 6/06), strike price (an integer)"
            ", quantity."
            " Quantity for BUY is always two unless specified. Quantity for SELL is always one."
            " the expiry should be in the format YYYYMMDD. YYYY is always 2025 unless specified."
            " Then return ONLY a string with all the following fields: symbol:..., contract_type:..., expiry:..., strike:..., action:..., quantity:... "
            " If some fields are not found, fill them with 'N/A'. be very very concise."
        )

    def reset_context_if_needed(self):
        current_date = datetime.now().date()
        if current_date != self.last_reset_date:
            print(f"[Reset] Clearing trade context for new day: {current_date}")
            self.trade_context.clear()
            self.last_reset_date = current_date

    def prompt(self, user_prompt: str):
        self.reset_context_if_needed()

        # Prepend prior trade context if symbol found
        for symbol, context in self.trade_context.items():
            if symbol in user_prompt.upper():
                context_text = (
                    f"Previous trade for {symbol}: symbol: {symbol}, contract_type: {context['contract_type']}, "
                    f"expiry: {context['expiry']}, strike: {context['strike']}."
                )
                user_prompt = context_text + " " + user_prompt
                break

        print("generating response")

        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=512,
                    temperature=0.3
                )
                break  # Success, break out of retry loop

            except openai.RateLimitError as e:
                retry_after = int(e.response.headers.get("Retry-After", 2 ** attempt))
                print(f"[429] Rate limited. Retrying after {retry_after} seconds...")
                time.sleep(retry_after)
            except HTTPStatusError as e:
                print(f"[ERROR] HTTP error: {e}")
                return f"Error: {e}"
            except Exception as e:
                print(f"[ERROR] Unexpected error: {e}")
                return f"Error: {e}"
        else:
            return "Error: Max retries exceeded due to rate limiting."

        print("returning response")
        output = response.choices[0].message.content.strip()
        print("Parsed output:", output)

        # Try to save or update trade context
        try:
            fields = [x.split(":")[1].strip() for x in output.split(",") if ":" in x]
            if len(fields) == 6:
                symbol, contract_type, expiry, strike, action, quantity = fields
                symbol = symbol.upper()

                if action == "BUY":
                    self.trade_context[symbol] = {
                        "contract_type": contract_type,
                        "expiry": expiry,
                        "strike": strike,
                        "position": int(quantity)
                    }

                elif action == "SELL":
                    if symbol in self.trade_context and self.trade_context[symbol]["position"] > 0:
                        self.trade_context[symbol]["position"] -= 1
                        print(f"[SELL] Reduced position for {symbol}: now {self.trade_context[symbol]['position']}")
                        if self.trade_context[symbol]["position"] == 0:
                            print(f"[CLOSE] No remaining position in {symbol}, removing from context.")
                            del self.trade_context[symbol]
                    else:
                        print(f"[SKIP] Cannot SELL {symbol}: no active position.")
                        return f"Cannot SELL {symbol}: no active position."

                elif action == "SPECULATE":
                    print(f"[SKIP] SPECULATE — not recorded.")
        except Exception as e:
            print(f"Could not save trade context: {e}")

        return output


# Test
llm = LLM("gpt-4o")   # SKIP: no position
