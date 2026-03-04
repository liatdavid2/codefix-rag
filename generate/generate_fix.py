import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import os
from dotenv import load_dotenv

from openai import OpenAI

from retrieve.retrieve_similar_code import retrieve_candidates, rerank


load_dotenv()

# Load OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def build_prompt(query, code_chunks):

    context = "\n\n".join(code_chunks)

    prompt = f"""
You are a senior Python engineer.

Bug description:
{query}

Function to fix:
{context}

Return ONLY the corrected Python function.

Rules:
- Do not explain
- Do not add debugging steps
- Do not generate example code
- Output only valid Python code

Corrected function:
"""

    return prompt


def generate_answer(query):

    # Retrieve similar code
    candidates = retrieve_candidates(query, top_n=50)

    # Rerank results
    results = rerank(query, candidates, k=1)

    # Limit code length
    code_chunks = [r["chunk"][:800] for r in results]

    prompt = build_prompt(query, code_chunks)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    answer = response.choices[0].message.content

    return answer


def main():

    query = input("Enter bug description: ")

    answer = generate_answer(query)

    print("\nGenerated Fix:\n")
    print(answer)


if __name__ == "__main__":
    main()