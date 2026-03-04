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

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    device_map="cpu",
    torch_dtype=torch.float32,
    low_cpu_mem_usage=True
    )

    return tokenizer, model


def build_prompt(query, code_chunks):

    context = "\n\n".join(code_chunks)

    prompt = f"""
You are an expert Python developer.

A bug was reported in a project.

Bug description:
{query}

Relevant code from the repository:
{context}

Task:
1. Identify the bug
2. Suggest a fix
3. Provide the corrected code

Answer format:

Explanation:
<short explanation>

Patch:
<fixed code>
"""

    return prompt


def generate_answer(query):

    candidates = retrieve_candidates(query, top_n=50)
    results = rerank(query, candidates, k=3)

    code_chunks = [r["chunk"][:800] for r in results]

    tokenizer, model = load_model()

    prompt = build_prompt(query, code_chunks)

    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    output = model.generate(
        **inputs,
        max_new_tokens=400,
        do_sample=True,
        temperature=0.2
        )

    answer = tokenizer.decode(output[0], skip_special_tokens=True)

    return answer


def main():

    query = input("Enter bug description: ")

    answer = generate_answer(query)

    print("\nGenerated Fix:\n")
    print(answer)


if __name__ == "__main__":
    main()