import json
import os
import subprocess
import faiss
from pathlib import Path
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv


DATASET = "datasets/processed/bugs_dataset.json"
REPOS_DIR = "datasets/repos"
INDEX_DIR = "datasets/index"

REPO_MAP = {
    "scrapy": "scrapy/scrapy"
}


def clone_repo(project):

    repo_name = REPO_MAP.get(project, f"{project}/{project}")
    repo_url = f"https://github.com/{repo_name}.git"

    repo_path = Path(REPOS_DIR) / project

    if repo_path.exists():
        print(f"Repository already exists: {repo_path}")
        return repo_path

    print(f"Cloning {repo_name}")

    subprocess.run(
        ["git", "clone", "--depth", "1", repo_url, str(repo_path)],
        check=True
    )

    return repo_path


def split_code(text, chunk_size=500):

    chunks = []

    for i in range(0, len(text), chunk_size):
        chunks.append(text[i:i + chunk_size])

    return chunks


def collect_code(repo_path, max_files=40):

    code_chunks = []
    file_count = 0

    for py_file in repo_path.rglob("*.py"):

        if "tests" in str(py_file):
            continue

        try:

            text = py_file.read_text(encoding="utf8")

            chunks = split_code(text)

            code_chunks.extend(chunks)

            file_count += 1

            if file_count >= max_files:
                break

        except Exception:
            pass

    return code_chunks


def build_index(chunks):

    print("Loading embedding model")

    # Load .env
    load_dotenv()

    # Read token
    hf_token = os.getenv("HF_TOKEN")

    # Load model
    model = SentenceTransformer(
        "sentence-transformers/all-MiniLM-L6-v2",
        token=hf_token
    )

    print("Model loaded successfully")

    print("Creating embeddings")

    embeddings = model.encode(
        chunks,
        show_progress_bar=True,
        convert_to_numpy=True
    )

    dimension = embeddings.shape[1]

    index = faiss.IndexFlatL2(dimension)

    index.add(embeddings)

    os.makedirs(INDEX_DIR, exist_ok=True)

    index_path = f"{INDEX_DIR}/code.index"
    chunks_path = f"{INDEX_DIR}/chunks.json"

    faiss.write_index(index, index_path)

    with open(chunks_path, "w", encoding="utf8") as f:
        json.dump(chunks, f)

    print("Index saved")
    print(f"Chunks stored: {len(chunks)}")


def main():

    all_chunks = []

    for project in REPO_MAP:

        repo_path = clone_repo(project)

        chunks = collect_code(repo_path)

        all_chunks.extend(chunks)

    print(f"Collected {len(all_chunks)} code chunks")

    build_index(all_chunks)


if __name__ == "__main__":
    main()