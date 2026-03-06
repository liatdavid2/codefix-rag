import json
import os

from retrieve.retrieve_similar_code import retrieve_candidates, rerank

DATASET = "datasets/processed/bugs_dataset.json"

TOP_K = 5


def normalize(name):

    name = name.replace(".py", "")
    name = name.replace("_", " ")
    name = name.lower()

    return name


def recall_at_k(retrieved_files, target_module):

    target_module_norm = normalize(target_module)

    target_tokens = target_module_norm.split()

    for f in retrieved_files:

        filename = normalize(os.path.basename(f))
        dirname = normalize(os.path.basename(os.path.dirname(f)))

        # 1. exact match
        if target_module_norm in filename:
            return 1

        if target_module_norm in dirname:
            return 1

        # 2. token match (http_request → request)
        for token in target_tokens:

            if token and token in filename:
                return 1

            if token and token in dirname:
                return 1

        # 3. __init__ always belongs to folder
        if filename == "__init__":
            if target_module_norm in dirname:
                return 1

    return 0


def evaluate():

    with open(DATASET, "r", encoding="utf8") as f:
        bugs = json.load(f)

    total = 0
    correct = 0

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

        # Step 1: retrieve
        candidates = retrieve_candidates(query, top_n=50)

        # Step 2: rerank
        results = rerank(query, candidates, k=TOP_K)

        retrieved_files = []

        for r in results:

            path = r.get("path", "")

            if path:
                retrieved_files.append(path)

        score = recall_at_k(retrieved_files, target_module)

        total += 1
        correct += score

        print("Bug:", bug["bug_id"])
        print("Target:", target)
        print("Target module:", target_module)
        print("Retrieved:", retrieved_files)
        print("Hit:", score)
        print("-" * 50)

    recall = correct / total if total else 0

    print()
    print("Evaluation Results")
    print("------------------")
    print("Total bugs:", total)
    print("Correct retrieval:", correct)
    print("Recall@5:", round(recall, 3))


if __name__ == "__main__":
    evaluate()