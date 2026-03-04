import os
import json
import subprocess
from pathlib import Path
import random

RAW_DATA = "datasets/raw/BugsInPy"
PROCESSED_DATA = "datasets/processed/bugs_dataset.json"


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


def collect_bug_examples():

    bugs = []

    projects_dir = Path(RAW_DATA) / "projects"

    if not projects_dir.exists():
        return bugs

    for project in projects_dir.iterdir():

        if not project.is_dir():
            continue

        for bug_folder in project.rglob("*"):

            if bug_folder.is_dir() and bug_folder.name.isdigit():

                bugs.append({
                    "bug_id": f"{project.name}_{bug_folder.name}",
                    "project": project.name,
                    "path": str(bug_folder)
                })

    return bugs


def build_dataset(sample_size=20):

    bugs = collect_bug_examples()

    if len(bugs) == 0:
        print("No bugs found")
        return

    sample = random.sample(bugs, min(sample_size, len(bugs)))

    os.makedirs("datasets/processed", exist_ok=True)

    with open(PROCESSED_DATA, "w") as f:
        json.dump(sample, f, indent=2)

    print(f"Saved dataset with {len(sample)} bugs")


if __name__ == "__main__":

    download_dataset()
    build_dataset()