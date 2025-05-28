class LLM:
    def __init__(self, model_name: str = "Qwen/Qwen3-0.6B"):
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(model_name)
        self.system_prompt = (
            "You are a helpful assistant that is an expert in quantitative options trading."
            "You will be given a prompt and you will respond with a helpful answer. "
            "You can think step by step to arrive at the answer."
            "Your task is to analyze the prompt and provide a detailed response."
            "You will be given a prompt that contains information about an options trade, "
            "including the option symbol, strike price, contract type (call or put), expiry date, entry price, and other details."
            "Your task is to analyze the prompt and turn it into a JSON object that contains the following fields: "
            "symbol, contract_type, expiry, price, action, quantity."
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