import json
import os

from retrieve.retrieve_similar_code import retrieve_candidates, rerank

DATASET = "datasets/processed/bugs_dataset.json"

TOP_K = 5


def recall_at_k(retrieved_files, target_module):

    for f in retrieved_files:

        filename = os.path.basename(f)
        filename = filename.replace(".py", "")

        if target_module in filename:
            return 1

    return 0


def evaluate():

    with open(DATASET, "r", encoding="utf8") as f:
        bugs = json.load(f)

    total = 0
    correct = 0

    for bug in bugs:

        query = bug["test_file"]

        # Step 1: retrieve candidates
        candidates = retrieve_candidates(query, top_n=50)

        # Step 2: rerank
        results = rerank(query, candidates, k=TOP_K)

        retrieved_files = []

        for r in results:

            path = r.get("path", "")

            if path:
                retrieved_files.append(path)

        target = bug["test_file"]

        # convert test file -> module
        target_module = os.path.basename(target)
        target_module = target_module.replace("test_", "")
        target_module = target_module.replace(".py", "")

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