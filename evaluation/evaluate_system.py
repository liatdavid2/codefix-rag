import json
import ast
import statistics
from difflib import SequenceMatcher

from generate.generate_fix import generate_answer
from evaluation.get_ground_truth import get_fix_patch
from pathlib import Path


DATASET = "datasets/processed/bugs_dataset.json"


def is_valid_python(code: str) -> bool:
    try:
        ast.parse(code)
        return True
    except Exception:
        return False


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def evaluate():

    with open(DATASET, "r", encoding="utf8") as f:
        dataset = json.load(f)

    total_samples = 0
    fixes_generated = 0
    syntax_valid = 0
    correct_fix = 0

    similarities = []
    rerank_scores = []

    for sample in dataset[:20]:

        bug_id = sample.get("bug_id")

        repo_path = Path("datasets/repos") / sample["project"]

        ground_truth = get_fix_patch(
            repo_path,
            sample["buggy_commit"],
            sample["fixed_commit"]
        )


        print("\n" + "=" * 80)
        print(f"BUG ID: {bug_id}")

        try:

            result = generate_answer(bug_id)

            generated_fix = result.get("corrected_function", "")
            rerank_score = result.get("rerank_score")

            total_samples += 1

            if generated_fix:
                fixes_generated += 1

                if is_valid_python(generated_fix):
                    syntax_valid += 1

            if rerank_score is not None:
                rerank_scores.append(rerank_score)

            sim = similarity(generated_fix, ground_truth) if ground_truth else 0
            similarities.append(sim)

            if sim > 0.8:
                correct_fix += 1

            print("\nGenerated Fix:\n")
            print(generated_fix)

            print("\nGround Truth:\n")
            print(ground_truth)

            print("\nSimilarity:", round(sim, 3))

            if sim > 0.8:
                print("MATCH: True")
            else:
                print("MATCH: False")

        except Exception as e:

            total_samples += 1
            print("ERROR:", e)

    metrics = {

        "total_samples": total_samples,

        "fix_generation_rate":
            fixes_generated / total_samples if total_samples else 0,

        "syntax_valid_rate":
            syntax_valid / total_samples if total_samples else 0,

        "fix_accuracy":
            correct_fix / total_samples if total_samples else 0,

        "average_similarity":
            statistics.mean(similarities) if similarities else 0,

        "average_rerank_score":
            statistics.mean(rerank_scores) if rerank_scores else None
    }

    print("\n" + "=" * 80)
    print("FINAL METRICS")
    print("=" * 80)

    for k, v in metrics.items():
        print(f"{k}: {v}")

    return metrics


if __name__ == "__main__":
    evaluate()