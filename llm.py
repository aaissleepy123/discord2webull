class LLM:
    def __init__(self, model_name: str = "Qwen/Qwen3-0.6B"):
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(model_name)
        self.system_prompt = (
            "You are a helpful assistant and an expert in quantitative options trading."
            " You will be given a prompt containing any kind of message — it could be a direct trade alert, news update, or a speculative idea."
            " Your task is to carefully analyze the message and infer whether the most appropriate action is one of the following:"
            " (1) BUY — if the message contains a clear, actionable trade entry signal;"
            " (2) SELL — if the message recommends taking profit, exiting a position, or closing a trade;"
            " (3) SPECULATE — if the message is general commentary, analysis, or news that suggests watching but not yet acting."
            " If relevant, extract the following details from the message: symbol, contract_type (call or put), expiry date, strike price, entry price, quantity."
            " Then return a string with all the following fields: symbol, contract_type, expiry, strike, entry, action, quantity."
            " If some fields are not found, fill them with 'N/A' or a reasonable default. Be concise and structured."
        )
    def _prepare_input(self, prompt: str):
        print("preparing input")
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        text = self.tokenizer.apply_chat_template(messages, 
                                                  tokenize=False, 
                                                  add_generation_prompt=True, 
                                                  enable_thinking=True)
        print("input prepared")
        return text

    def prompt(self, prompt: str):
        print("generating response")
        text = self._prepare_input(prompt)
        model_inputs = self.tokenizer([text], return_tensors="pt")
        generated_ids = self.model.generate(
            **model_inputs,
            max_new_tokens=32768
        )
        output_ids = generated_ids[0][len(model_inputs.input_ids[0]):].tolist() 
        
        try:
            index = len(output_ids) - output_ids[::-1].index(151668)
        except ValueError:
            index = 0
        
        #thinking_content = self.tokenizer.decode(output_ids[:index], skip_special_tokens=True).strip("\n")
        content = self.tokenizer.decode(output_ids[index:], skip_special_tokens=True).strip("\n")
        print('returning response')
        return content
    
LLM = LLM()
print(LLM.prompt("AAPL 150C 2024-01-19 1.50 10"))  # Example prompt to test the LLM