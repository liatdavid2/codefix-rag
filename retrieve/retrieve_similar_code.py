import json
import os
import faiss
from dotenv import load_dotenv

INDEX_DIR = "datasets/index"

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")

if HF_TOKEN:
    os.environ["HUGGINGFACE_HUB_TOKEN"] = HF_TOKEN


EMBED_MODEL = None
RERANK_MODEL = None

INDEX = None
CHUNKS = None


def get_embed_model():

    global EMBED_MODEL

    if EMBED_MODEL is None:

        from sentence_transformers import SentenceTransformer

        print("Loading embedding model...")

        EMBED_MODEL = SentenceTransformer(
            "BAAI/bge-small-en"
        )

    return EMBED_MODEL


def get_rerank_model():

    global RERANK_MODEL

    if RERANK_MODEL is None:

        from sentence_transformers import CrossEncoder

        print("Loading reranker model...")

        RERANK_MODEL = CrossEncoder(
            "cross-encoder/ms-marco-MiniLM-L-6-v2"
        )

    return RERANK_MODEL


def load_index():

    global INDEX, CHUNKS

    if INDEX is None:

        print("Loading FAISS index...")

        INDEX = faiss.read_index(
            f"{INDEX_DIR}/code.index"
        )

        with open(
            f"{INDEX_DIR}/chunks.json",
            "r",
            encoding="utf8"
        ) as f:

            CHUNKS = json.load(f)

    return INDEX, CHUNKS


def retrieve_candidates(query, top_n=50):

    embed_model = get_embed_model()

    index, chunks = load_index()

    # improve embedding for code search
    query = "Find similar buggy Python code:\n" + query

    query_embedding = embed_model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    distances, indices = index.search(
        query_embedding,
        top_n
    )

    results = []

    for score, idx in zip(
        distances[0],
        indices[0]
    ):

        if idx == -1:
            continue

        chunk_data = chunks[idx]

        # chunks.json may contain raw code strings
        if isinstance(chunk_data, str):

            results.append(
                {
                    "faiss_score": float(score),
                    "code": chunk_data,
                    "path": "unknown_file.py"
                }
            )

        else:

            results.append(
                {
                    "faiss_score": float(score),
                    "code": chunk_data["code"],
                    "path": chunk_data.get("path", "unknown_file.py")
                }
            )

    return results


def rerank(query, candidates, k=5):

    rerank_model = get_rerank_model()

    pairs = [
        (query, c["code"])
        for c in candidates
    ]

    scores = rerank_model.predict(pairs)

    merged = []

    for candidate, rerank_score in zip(
        candidates,
        scores
    ):

        merged.append(
            {
                "rerank_score": float(rerank_score),
                "faiss_score": candidate["faiss_score"],
                "code": candidate["code"],
                "path": candidate["path"]
            }
        )

    merged.sort(
        key=lambda x: x["rerank_score"],
        reverse=True
    )

    return merged[:k]


def main():

    query = input("Enter buggy code or bug description: ")

    print("Retrieving similar code...")

    candidates = retrieve_candidates(
        query,
        top_n=50
    )

    print("Reranking results...")

    results = rerank(
        query,
        candidates,
        k=5
    )

    print("\nTop similar code (reranked):\n")

    for r in results:

        print("-----")

        print(
            "RerankScore:",
            r["rerank_score"],
            "| FaissScore:",
            r["faiss_score"]
        )

        print("File:", r["path"])
        print(r["code"][:500])


if __name__ == "__main__":
    main()