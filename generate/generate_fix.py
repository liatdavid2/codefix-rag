import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

from dotenv import load_dotenv

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

from retrieve.retrieve_similar_code import retrieve_candidates, rerank


load_dotenv()

MODEL_NAME = "deepseek-ai/deepseek-coder-1.3b-instruct"

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
You are a senior Python engineer fixing a bug in a codebase.

BUG DESCRIPTION:
{query}

CODE CONTEXT:
{context}

Your task:
1. Identify the bug
2. Explain why it happens
3. Provide corrected code

Respond ONLY in this format:

Explanation:
<short explanation>

Patch:
<fixed code>

Answer:
"""

    return prompt


def generate_answer(query):

    # Retrieve similar code
    candidates = retrieve_candidates(query, top_n=50)

    # Rerank results
    results = rerank(query, candidates, k=3)

    # Limit code length
    code_chunks = [r["chunk"][:300] for r in results]

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