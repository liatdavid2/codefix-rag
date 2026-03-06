import json
import os
import subprocess
import tempfile
from difflib import SequenceMatcher

from retrieve.retrieve_similar_code import retrieve_candidates, rerank


DATASET = "datasets/processed/bugs_dataset.json"
GENERATED_FIXES = "datasets/learn/bug_fix_pairs.jsonl"

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

    if target_module_norm in filename:
        return True

    if target_module_norm in dirname:
        return True

    for token in target_tokens:

        if token and token in filename:
            return True

        if token and token in dirname:
            return True

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


def load_generated_fixes():

    fixes = {}

    if not os.path.exists(GENERATED_FIXES):
        return fixes

    with open(GENERATED_FIXES, "r", encoding="utf8") as f:

        for line in f:

            item = json.loads(line)

            bug_id = item.get("bug_id")
            fix = item.get("generated_fix")

            if bug_id is not None:
                fixes[bug_id] = fix

    return fixes


def get_ground_truth_patch(repo_path, buggy_commit, fixed_commit):

    try:

        result = subprocess.run(
            ["git", "diff", buggy_commit, fixed_commit],
            cwd=repo_path,
            capture_output=True,
            text=True
        )

        return result.stdout

    except Exception:
        return ""


def evaluate():

    with open(DATASET, "r", encoding="utf8") as f:
        bugs = json.load(f)

    generated_fixes = load_generated_fixes()

    metrics = {
        k: {
            "recall": 0
        }
        for k in KS
    }

    gen_metrics = {
        "syntax": 0,
        "lint": 0,
        "similarity": 0
    }

    total = 0
    gen_total = 0

    for bug in bugs:
        print("bug:", bug["bug_id"], "has fix:", bug["bug_id"] in generated_fixes)
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

        candidates = retrieve_candidates(query, top_n=50)

        results = rerank(query, candidates, k=max(KS))

        retrieved_files = []

        for r in results:

            path = r.get("path", "")

            if path:
                retrieved_files.append(path)

        for k in KS:

            top_k = retrieved_files[:k]

            hits = 0

            for f in top_k:
                if is_hit(f, target_module):
                    hits += 1

            recall = 1 if hits > 0 else 0

            metrics[k]["recall"] += recall

        repo_path = f"datasets/repos/{bug['project']}"

        gt_patch = get_ground_truth_patch(
            repo_path,
            bug.get("buggy_commit"),
            bug.get("fixed_commit")
        )

        generated_fix = generated_fixes.get(bug.get("bug_id"), "")

        if bug["bug_id"] in generated_fixes:

            syntax_ok = check_syntax(generated_fix)
            lint_ok = check_lint(generated_fix)
            sim = patch_similarity(generated_fix, gt_patch)

            gen_metrics["syntax"] += syntax_ok
            gen_metrics["lint"] += lint_ok
            gen_metrics["similarity"] += sim

            gen_total += 1

        total += 1

    print("generated fixes:", len(generated_fixes))
    print("Retrieval Evaluation")
    print("--------------------")
    print("Total bugs:", total)
    print()

    print(f"{'K':<6}{'Recall':<12}")

    for k in KS:

        recall = metrics[k]["recall"] / total

        print(
            f"@{k:<5}"
            f"{recall:<12.3f}"
        )

    if gen_total > 0:

        print()
        print("Generation Evaluation")
        print("---------------------")

        syntax_rate = gen_metrics["syntax"] / gen_total
        lint_rate = gen_metrics["lint"] / gen_total
        sim_score = gen_metrics["similarity"] / gen_total

        print(f"Syntax validity: {syntax_rate:.3f}")
        print(f"Lint pass rate: {lint_rate:.3f}")
        print(f"Patch similarity: {sim_score:.3f}")


if __name__ == "__main__":
    evaluate()