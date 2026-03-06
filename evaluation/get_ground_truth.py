import json
import subprocess
from pathlib import Path


DATASET = "datasets/processed/bugs_dataset.json"
REPOS_DIR = "datasets/repos"


def get_patch(repo_path, buggy_commit, fixed_commit):

    cmd = [
        "git",
        "-C",
        str(repo_path),
        "diff",
        buggy_commit,
        fixed_commit
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )

    return result.stdout


def main():

    with open(DATASET, "r") as f:
        bugs = json.load(f)

    for bug in bugs:

        project = bug["project"]

        repo_path = Path(REPOS_DIR) / project

        buggy = bug["buggy_commit"]
        fixed = bug["fixed_commit"]

        print(f"Processing {bug['bug_id']}")

        patch = get_patch(repo_path, buggy, fixed)

        bug["ground_truth_patch"] = patch

    with open(DATASET, "w") as f:
        json.dump(bugs, f, indent=2)

    print("Finished generating ground truth patches")


if __name__ == "__main__":
    main()