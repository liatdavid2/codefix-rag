import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import json
import os
from dotenv import load_dotenv
from openai import OpenAI

from retrieve.retrieve_similar_code import retrieve_candidates, rerank
from validation.validate_patch import validate_fix


load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def read_code_input() -> str:
    """
    Read multiline code snippet from the user.
    Finish input by typing END on a new line.
    """

    print("Paste buggy code. Type END on a new line when finished:\n")

    lines = []

    while True:
        line = input()

        if line.strip() == "END":
            break

        lines.append(line)

    return "\n".join(lines)


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
        context += f"\n\nExample {i+1}:\n{chunk}"

    prompt = f"""
You are a senior Python engineer.

Buggy code:
{query}

Relevant code examples from the repository:
{context}

Task:
1) Identify the bug in the provided code.
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
- Only modify the function body, do not modify code outside the function.
- Diff must be unified diff format (starts with --- / +++ and @@ hunks).
- corrected_function must be a single Python function definition.
"""

    return prompt.strip()

def detect_exception(code: str):

    try:
        # isolated namespace
        sandbox_globals = {"__builtins__": {}}
        sandbox_locals = {}

        exec(code, sandbox_globals, sandbox_locals)

        return None

    except Exception as e:

        return type(e).__name__

def _safe_parse_json(text: str) -> dict:

    text = text.strip()

    if text.startswith("```"):
        text = text.replace("```json", "")
        text = text.replace("```", "")
        text = text.strip()

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
    exception = detect_exception(query)
    query_text = f"""
        Python bug fixing task

        Exception: {exception}

        Buggy code:
        {query}

        Find similar code patterns and suggest a fix.
        """
    candidates = retrieve_candidates(query_text, top_n=top_n)
    results = rerank(query_text, candidates, k=top_k)

    print("\nTop retrieved code snippets:\n")

    for i, r in enumerate(results):

        #path = r.get("path", "unknown_file.py")
        score = r.get("rerank_score", "?")
        code = r.get("code", "")

        snippet = code[:300]

        print(f"\n[{i+1}] rerank_score={score}\n")
        print(snippet)
        print("\n" + "-" * 60)

    code_chunks = [
        f"""
        File: {r.get("path")}
        Object: {r.get("object")}
        Type: {r.get("type")}

        {r.get("code")}
        """[:800]
        for r in results
    ]

    prompt = build_prompt(query, code_chunks)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = (response.choices[0].message.content or "").strip()

    return _safe_parse_json(raw)


def main():

    code_snippet = read_code_input()

    if not code_snippet:
        print("Code snippet is required.")
        return

    result = generate_answer(code_snippet)

    explanation = (result.get("explanation") or "").strip()
    diff = (result.get("diff") or "").rstrip()
    corrected = (result.get("corrected_function") or "").rstrip()

    print("\nExplanation:\n")
    print(explanation if explanation else "(none)")

    print("\nGit Diff Patch:\n")
    print(diff if diff else "(none)")

    print("\nCorrected Function:\n")
    print(corrected if corrected else "(none)")

    # ---------- NEW PART ----------
    from validation.validate_patch import validate_fix

    validation = validate_fix(
        corrected,
        result.get("rerank_score", 0.0)
    )

    print("\nValidation:\n")
    print(validation)


if __name__ == "__main__":
    main()