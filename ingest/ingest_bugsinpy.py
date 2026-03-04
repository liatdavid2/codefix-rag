import os
import json
import subprocess
from pathlib import Path
import random

RAW_DATA = "datasets/raw/BugsInPy"
OUTPUT_DATA = "datasets/processed/bugs_dataset.json"


def download_dataset():

    if os.path.exists(RAW_DATA):
        print("Dataset already downloaded")
        return

    print("Downloading BugsInPy dataset...")

    subprocess.run([
        "git",
        "clone",
        "https://github.com/soarsmu/BugsInPy.git",
        RAW_DATA
    ])


def parse_bug_info(bug_path):

    info = {}

    info_file = Path(bug_path) / "bug.info"

    if not info_file.exists():
        return info

    with open(info_file, "r", encoding="utf8") as f:

        for line in f:

            if "=" not in line:
                continue

            key, value = line.split("=", 1)

            info[key.strip()] = value.strip().replace('"', "")

    return info


def collect_bug_examples():

    bugs = []

    projects_dir = Path(RAW_DATA) / "projects"

    for project in projects_dir.iterdir():

        if not project.is_dir():
            continue

        bugs_dir = project / "bugs"

        if not bugs_dir.exists():
            continue

        for bug_folder in bugs_dir.iterdir():

            if not bug_folder.is_dir():
                continue

            info = parse_bug_info(bug_folder)

            bugs.append({
                "bug_id": f"{project.name}_{bug_folder.name}",
                "project": project.name,
                "python_version": info.get("python_version", ""),
                "buggy_commit": info.get("buggy_commit_id", ""),
                "fixed_commit": info.get("fixed_commit_id", ""),
                "test_file": info.get("test_file", ""),
                "path": str(bug_folder)
            })

    return bugs


def build_dataset(sample_size=20):

    bugs = collect_bug_examples()

    sample = random.sample(bugs, min(sample_size, len(bugs)))

    os.makedirs("datasets/processed", exist_ok=True)

    with open(OUTPUT_DATA, "w", encoding="utf8") as f:
        json.dump(sample, f, indent=2)

    print(f"Saved dataset with {len(sample)} bugs")


if __name__ == "__main__":

    download_dataset()
    build_dataset()