import json
import os
import subprocess
import faiss
import ast
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


def clean_code(text):
    return "\n".join(
        line for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    )


def split_large_chunk(text, max_chars=1200):

    if len(text) <= max_chars:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        chunks.append(text[start:start + max_chars])
        start += max_chars

    return chunks


def collect_code(repo_path):

    code_chunks = []

    for py_file in Path(repo_path).rglob("*.py"):

        path_str = str(py_file)

        if any(x in path_str for x in ["tests", "migrations", "build", "__pycache__"]):
            continue

        try:

            source = py_file.read_text(encoding="utf8")

            tree = ast.parse(source)

            lines = source.splitlines()

            for node in ast.walk(tree):

                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):

                    start = node.lineno - 1
                    end = node.end_lineno

                    code = "\n".join(lines[start:end])

                    code = clean_code(code)

                    docstring = ast.get_docstring(node) or ""

                    metadata = f"""
File: {py_file}
Object: {node.name}
Type: {type(node).__name__}
Docstring: {docstring}
"""

                    full_chunk = metadata + "\n" + code

                    split_chunks = split_large_chunk(full_chunk)

                    code_chunks.extend(split_chunks)

        except Exception:
            continue

    return code_chunks


def build_index(chunks):

    print("Loading embedding model")

    load_dotenv()

    hf_token = os.getenv("HF_TOKEN")

    model = SentenceTransformer(
        "BAAI/bge-small-en",
        token=hf_token
    )

    print("Model loaded successfully")

    print("Creating embeddings")

    embeddings = model.encode(
        chunks,
        batch_size=128,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    dimension = embeddings.shape[1]

    index = faiss.IndexFlatIP(dimension)

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