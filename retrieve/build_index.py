import json
import os
import subprocess
import faiss
from pathlib import Path
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import ast
from pathlib import Path


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


def collect_code(repo_path):

    code_chunks = []

    for py_file in Path(repo_path).rglob("*.py"):

        try:
            source = py_file.read_text(encoding="utf8")
            tree = ast.parse(source)

            for node in ast.walk(tree):

                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):

                    start = node.lineno - 1
                    end = node.end_lineno

                    lines = source.splitlines()[start:end]
                    chunk = "\n".join(lines)

                    code_chunks.append(chunk)

        except Exception:
            continue

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