import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

from dotenv import load_dotenv

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

from retrieve.retrieve_similar_code import retrieve_candidates, rerank


load_dotenv()

#MODEL_NAME = "deepseek-ai/deepseek-coder-1.3b-instruct"
MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"

tokenizer = None
model = None


def load_model():
    global tokenizer, model

    if model is not None:
        return tokenizer, model

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME,
        trust_remote_code=True
    )

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        device_map="cpu",
        torch_dtype=torch.float32,
        low_cpu_mem_usage=True,
        trust_remote_code=True
    )

    return tokenizer, model


def build_prompt(query, code_chunks):

    context = "\n\n".join(code_chunks)

    prompt = f"""
    You are a senior Python engineer.

    Bug description:
    {query}

    Function to fix:
    {context}

    Return ONLY the corrected function.
    Do not add explanations.
    Do not generate unrelated code.
    """

    return prompt


def generate_answer(query):

    # Retrieve similar code
    candidates = retrieve_candidates(query, top_n=50)

    # Rerank results
    results = rerank(query, candidates, k=3)

    # Limit code length
    code_chunks = [r["chunk"][:800] for r in results]

    tokenizer, model = load_model()

    prompt = build_prompt(query, code_chunks)

    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=4096
    ).to(model.device)

    with torch.no_grad():

        output = model.generate(
            **inputs,
            max_new_tokens=400,
            do_sample=True,
            temperature=0.2,
            pad_token_id=tokenizer.eos_token_id
        )

    # Decode only generated tokens
    generated_tokens = output[0][inputs["input_ids"].shape[1]:]
    answer = tokenizer.decode(generated_tokens, skip_special_tokens=True)

    return answer


def main():

    query = input("Enter bug description: ")

    answer = generate_answer(query)

    print("\nGenerated Fix:\n")
    print(answer)


if __name__ == "__main__":
    main()