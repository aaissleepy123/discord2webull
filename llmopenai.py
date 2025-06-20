import openai
from httpx import HTTPStatusError
from openai import OpenAI
from dotenv import load_dotenv
import os
from datetime import datetime
import time
from ib_insync import IB

# Create a dedicated IBKR connection for LLM logic
ib_llm = IB()
ib_llm.connect("127.0.0.1", 4002, clientId=2)

# Verify connection
if ib_llm.isConnected():
    print("[LLM IBKR] Connected to IBKR with clientId=2")
else:
    print("[LLM IBKR] Failed to connect!")

load_dotenv()

class LLM:
    def __init__(self, model_name: str = "gpt-4o"):
        self.model_name = model_name
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def fetch_ibkr_positions_string(self, ib=ib_llm):
        positions = ib.positions()
        summaries = [
            f"{'LONG' if pos.position > 0 else 'SHORT'} {abs(pos.position)} "
            f"{pos.contract.symbol} {pos.contract.right} {pos.contract.strike} {pos.contract.lastTradeDateOrContractMonth}"
            for pos in positions if pos.position != 0
        ]
        return " | ".join(summaries) if summaries else "No open positions"

    def build_system_prompt(self, ibkr_summary):
        return (
            f"You are the best trader and an expert in quantitative options trading. "
            f"Current IBKR open positions: {ibkr_summary}. "
            f"You will be given a prompt containing any kind of message — it could be a direct trade alert, news update, or a speculative idea. "
            f"Your task is to carefully analyze the message and infer whether the most appropriate action is one of the following: "
            f"(1) BUY — if the message contains a clear, actionable trade entry signal; "
            f"(2) SELL — if the message recommends trimming, taking profit, or exiting a position; "
            f"(3) SPECULATE — if the message is commentary or watch-only. "
            f"The action can only be one of BUY, SELL, and SPECULATE. "
            f"You can only return SELL if your current holding of this quantity is strictly larger than 0. "
            f"If relevant, extract: symbol, contract_type (call or put), expiry (YYYYMMDD), strike (int), quantity (int). "
            f"Quantity for BUY is 2 unless specified. Quantity for SELL is 1 unless specified. "
            f"If any field is missing, fill with 'N/A'. Return only: symbol:..., contract_type:..., expiry:..., strike:..., action:..., quantity:... "
            f"However, if any field is missing but the current IBKR open positions contain a symbol that matches the symbol in the message, "
            f"you should infer the missing fields from the IBKR open positions. "
            f"For example, if you have QQQ 9/8 525 call in your IBKR positions, and my message says 'trim qqq calls', "
            f"you should return: symbol: QQQ, contract_type: C, expiry: 20250908, strike: 525, action: SELL, quantity: 1"
            f"The expiry must be 2025 unless I explicitly specify otherwise. If unsure, default to a valid 2025 expiry date."
        )

    def prompt(self, user_prompt: str, ib=ib_llm):
        ibkr_summary = self.fetch_ibkr_positions_string(ib)
        system_prompt = self.build_system_prompt(ibkr_summary)

        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=512,
                    temperature=0.3
                )
                break
            except openai.RateLimitError as e:
                retry_after = int(e.response.headers.get("Retry-After", 2 ** attempt))
                print(f"[429] Rate limited. Retry after {retry_after}s...")
                time.sleep(retry_after)
            except HTTPStatusError as e:
                print(f"[HTTP ERROR] {e}")
                return f"HTTP Error: {e}"
            except Exception as e:
                print(f"[ERROR] {e}")
                return f"Error: {e}"
        else:
            return "Error: Max retries exceeded."

        output = response.choices[0].message.content.strip()
        print("[LLM] LLM Output:", output)
        return output
