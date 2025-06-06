# # class LLM:
# #     def __init__(self, model_name: str = "Qwen/Qwen3-0.6B"):
# #         from transformers import AutoModelForCausalLM, AutoTokenizer
# #         self.tokenizer = AutoTokenizer.from_pretrained(model_name)
# #         self.model = AutoModelForCausalLM.from_pretrained(model_name)
# #         self.system_prompt = (
# #             "You are the best trader and an expert in quantitative options trading."
# #             " You will be given a prompt containing any kind of message — it could be a direct trade alert, news update, or a speculative idea."
# #             " Your task is to carefully analyze the message and infer whether the most appropriate action is one of the following:"
# #             " (1) BUY — if the message contains a clear, actionable trade entry signal;"
# #             " (2) SELL — if the message recommends trimming, trim, taking profit, exiting a position, or closing a trade;"
# #             " (3) SPECULATE — if the message is saying im looking at, general commentary, analysis, or news that suggests watching but not yet acting."
# #             "the action can only be one of BUY, SELL and SPECULATE. things like taking profit and trimming means SELL, grabbing means buying"
# #             " If relevant, extract the following details from the message: symbol, contract_type (call or put), expiry date usually in the format of a number / another number, strike price(usually an integer without a slash, entry price, quantity."
# #             " Quantity is always two unless specified."
# #             " Then return a string with all the following fields: symbol, contract_type, expiry, strike, entry, action, quantity. "
# #             " If some fields are not found, fill them with 'N/A' or a reasonable default. Be concise and structured."
# #         )
# #     def _prepare_input(self, prompt: str):
# #         print("preparing input")
# #         messages = [
# #             {"role": "system", "content": self.system_prompt},
# #             {"role": "user", "content": prompt}
# #         ]
# #         text = self.tokenizer.apply_chat_template(messages,
# #                                                   tokenize=False,
# #                                                   add_generation_prompt=True,
# #                                                   enable_thinking=True)
# #         print("input prepared")
# #         return text
# #
# #     def prompt(self, prompt: str):
# #         print("generating response")
# #         text = self._prepare_input(prompt)
# #         model_inputs = self.tokenizer([text], return_tensors="pt")
# #         generated_ids = self.model.generate(
# #             **model_inputs,
# #             max_new_tokens=32768
# #         )
# #         output_ids = generated_ids[0][len(model_inputs.input_ids[0]):].tolist()
# #
# #         try:
# #             index = len(output_ids) - output_ids[::-1].index(151668)
# #         except ValueError:
# #             index = 0
# #
# #         #thinking_content = self.tokenizer.decode(output_ids[:index], skip_special_tokens=True).strip("\n")
# #         content = self.tokenizer.decode(output_ids[index:], skip_special_tokens=True).strip("\n")
# #         print('returning response')
# #         return content
# #
# # llm = LLM()
# # print(llm.prompt("I'm looking at TSLA 310 C 6/6")) # Example prompt to test the LLM
# import os
# from openai import OpenAI
# from dotenv import load_dotenv
# load_dotenv()
#
# from openai import OpenAI
# import os
# from datetime import datetime
#
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
            " (1) BUY — if the message contains a clear, actionable trade entry signal;"
            " (2) SELL — if the message recommends trimming, trim, taking profit, exiting a position, or closing a trade"
            " (3) SPECULATE — if the message is saying im looking at, general commentary, analysis, or news that suggests watching but not yet acting."
            " The action can only be one of BUY, SELL, and SPECULATE. Things like taking profit and trimming mean SELL, grabbing means buying."
            " you can only return SELL if your current holding of this quantity is strictly larger than 0."
            " If relevant, extract the following details from the message: symbol, contract_type (call or put), expiry date (e.g. 6/06), strike price (an integer), entry price, quantity."
            " Quantity for BUY is always two unless specified. Quantity for SELL is always one."
            " Then return a string with all the following fields: symbol:..., contract_type:..., expiry:..., strike:..., entry:..., action:..., quantity:... "
            " If some fields are not found, fill them with 'N/A'."
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
                    f"expiry: {context['expiry']}, strike: {context['strike']}, entry: {context['entry']}."
                )
                user_prompt = context_text + " " + user_prompt
                break

        print("generating response")
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=512,
            temperature=0.3
        )
        print("returning response")
        output = response.choices[0].message.content.strip()
        print("Parsed output:", output)

        # Try to save or update trade context
        try:
            fields = [x.split(":")[1].strip() for x in output.split(",") if ":" in x]
            if len(fields) == 7:
                symbol, contract_type, expiry, strike, entry, action, quantity = fields
                symbol = symbol.upper()

                if action == "BUY":
                    self.trade_context[symbol] = {
                        "contract_type": contract_type,
                        "expiry": expiry,
                        "strike": strike,
                        "entry": entry,
                        "position": int(quantity)  # Start with full position
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
llm = LLM("gpt-4o")
print(llm.prompt("META 705 C 6/6 @$1.87"))         # BUY
print(llm.prompt("META back at breakeven"))        # SELL (position becomes 1)
print(llm.prompt("META trimming again"))           # SELL (position becomes 0, removed)
print(llm.prompt("META trimming final time"))      # SKIP: no position
