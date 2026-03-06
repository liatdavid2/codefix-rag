import json
import os
import subprocess
import tempfile
from difflib import SequenceMatcher

from retrieve.retrieve_similar_code import retrieve_candidates, rerank

DATASET = "datasets/processed/bugs_dataset.json"

KS = [1, 5, 10]


def normalize(name):

    name = name.replace(".py", "")
    name = name.replace("_", " ")
    name = name.lower()

    return name


def is_hit(file_path, target_module):

    target_module_norm = normalize(target_module)

    target_tokens = target_module_norm.split()

    filename = normalize(os.path.basename(file_path))
    dirname = normalize(os.path.basename(os.path.dirname(file_path)))

    # exact match
    if target_module_norm in filename:
        return True

    if target_module_norm in dirname:
        return True

    # token match
    for token in target_tokens:

        if token and token in filename:
            return True

        if token and token in dirname:
            return True

    # __init__ case
    if filename == "__init__":
        if target_module_norm in dirname:
            return True

    return False


def check_syntax(code):

    try:
        compile(code, "<string>", "exec")
        return 1
    except Exception:
        return 0


def check_lint(code):

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(code)
        path = f.name

    result = subprocess.run(
        ["flake8", path],
        capture_output=True,
        text=True
    )

    return 1 if result.returncode == 0 else 0


def patch_similarity(a, b):

    if not a or not b:
        return 0

    return SequenceMatcher(None, a, b).ratio()



def evaluate():

    with open(DATASET, "r", encoding="utf8") as f:
        bugs = json.load(f)

    metrics = {
        k: {
            "recall": 0,
            "precision": 0,
            "f1": 0
        }
        for k in KS
    }

    gen_metrics = {
    "syntax": 0,
    "lint": 0,
    "similarity": 0
    }

    total = 0

    for bug in bugs:

        target = bug["test_file"]

        target_module = os.path.basename(target)
        target_module = target_module.replace("test_", "")
        target_module = target_module.replace(".py", "")

        query = f"""
Project: {bug['project']}

Bug related to test:
{target}

Target module:
{target_module}
"""

        # retrieve
        candidates = retrieve_candidates(query, top_n=50)

        # rerank
        results = rerank(query, candidates, k=max(KS))

        retrieved_files = []

        for r in results:

            path = r.get("path", "")

            if path:
                retrieved_files.append(path)

        # compute metrics per K
        for k in KS:

            top_k = retrieved_files[:k]

            hits = 0

            for f in top_k:
                if is_hit(f, target_module):
                    hits += 1

            recall = 1 if hits > 0 else 0
            precision = hits / k

            if precision + recall > 0:
                f1 = 2 * precision * recall / (precision + recall)
            else:
                f1 = 0

            metrics[k]["recall"] += recall
            metrics[k]["precision"] += precision
            metrics[k]["f1"] += f1

        total += 1

    print()
    print("Evaluation Results")
    print("------------------")
    print("Total bugs:", total)
    print()

    print(f"{'K':<6}{'Recall':<12}")

    for k in KS:

        recall = metrics[k]["recall"] / total

        print(
            f"@{k:<5}"
            f"{recall:<12.3f}"
        )


if __name__ == "__main__":
    evaluate()