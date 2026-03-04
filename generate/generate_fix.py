import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import json
import os
from dotenv import load_dotenv
from openai import OpenAI

from retrieve.retrieve_similar_code import retrieve_candidates, rerank


load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def build_prompt(query: str, code_chunks: list[str]) -> str:
    """
    Ask the LLM for:
    - short explanation
    - unified diff patch
    - corrected function
    Return as strict JSON to make parsing reliable.
    """

    context = ""
    for i, chunk in enumerate(code_chunks):
        context += (
            f"\n\n[Example {i+1}]\n"
            f"```python\n{chunk}\n```"
        )

    prompt = f"""
You are a senior Python engineer.

Bug description:
{query}

Relevant code examples from the repository:
{context}

Task:
1) Identify the most likely buggy function among the examples and fix it.
2) Return:
   - a short explanation (1-2 sentences)
   - a unified git diff patch for the fix
   - the full corrected Python function

Output format:
Return ONLY valid JSON (no markdown, no extra text) with the following schema:

{{
  "explanation": "string",
  "diff": "string",
  "corrected_function": "string"
}}

Rules:
- Keep the original function signature.
- Diff must be unified diff format (starts with --- / +++ and @@ hunks).
- corrected_function must be a single Python function definition.
- Do not include tests, debug steps, or extra commentary outside JSON.
"""

    return prompt.strip()


def _safe_parse_json(text: str) -> dict:

    text = text.strip()

    # remove markdown code fences
    if text.startswith("```"):
        text = text.replace("```json", "")
        text = text.replace("```", "")
        text = text.strip()

    # try extracting JSON block
    first = text.find("{")
    last = text.rfind("}")

    if first != -1 and last != -1:
        text = text[first:last + 1]

    try:
        return json.loads(text)

    except Exception as e:

        print("JSON parse error:", e)

        return {
            "explanation": "Failed to parse model output as JSON.",
            "diff": "",
            "corrected_function": text
        }


def generate_answer(query: str, top_n: int = 50, top_k: int = 3) -> dict:

    candidates = retrieve_candidates(query, top_n=top_n)

    results = rerank(query, candidates, k=top_k)

    print("\nTop retrieved code snippets:\n")

    for i, r in enumerate(results):

        path = r.get("path", "unknown_file.py")
        score = r.get("score", "?")
        code = r["chunk"]

        snippet = code[:300]

        print(f"\n[{i+1}] File: {path}  score={score}\n")
        print(snippet)
        print("\n" + "-"*60)

    # Provide a bit more context per snippet, but keep it bounded
    code_chunks = [r["chunk"][:1200] for r in results]

    prompt = build_prompt(query, code_chunks)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = (response.choices[0].message.content or "").strip()
    return _safe_parse_json(raw)


def main():
    query = input("Enter bug description: ").strip()
    if not query:
        print("Bug description is required.")
        return

    result = generate_answer(query)

    explanation = (result.get("explanation") or "").strip()
    diff = (result.get("diff") or "").rstrip()
    corrected = (result.get("corrected_function") or "").rstrip()

    print("\nExplanation:\n")
    print(explanation if explanation else "(none)")

    print("\nGit Diff Patch:\n")
    print(diff if diff else "(none)")

    print("\nCorrected Function:\n")
    print(corrected if corrected else "(none)")


if __name__ == "__main__":
    main()