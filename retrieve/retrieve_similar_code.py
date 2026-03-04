import json
import os
import faiss
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer, CrossEncoder


INDEX_DIR = "datasets/index"


# Load environment variables
load_dotenv()

# Read token from .env
HF_TOKEN = os.getenv("HF_TOKEN")

# Pass token to HuggingFace environment
if HF_TOKEN:
    os.environ["HUGGINGFACE_HUB_TOKEN"] = HF_TOKEN


# Load models once
EMBED_MODEL = SentenceTransformer(
    "BAAI/bge-small-en"
)

RERANK_MODEL = CrossEncoder(
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
)


def load_index():

    index = faiss.read_index(f"{INDEX_DIR}/code.index")

    with open(f"{INDEX_DIR}/chunks.json", "r", encoding="utf8") as f:
        chunks = json.load(f)

    return index, chunks


def retrieve_candidates(query, top_n=50):

    index, chunks = load_index()

    query_embedding = EMBED_MODEL.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    distances, indices = index.search(query_embedding, top_n)

    results = []

    for score, idx in zip(distances[0], indices[0]):

        if idx == -1:
            continue

        results.append((score, chunks[idx]))

    return results


def rerank(query, candidates, k=5):

    pairs = [(query, chunk) for _, chunk in candidates]

    scores = RERANK_MODEL.predict(pairs)

    merged = []

    for (faiss_score, chunk), rerank_score in zip(candidates, scores):

        merged.append(
            {
                "rerank_score": float(rerank_score),
                "faiss_score": float(faiss_score),
                "chunk": chunk
            }
        )

    merged.sort(key=lambda x: x["rerank_score"], reverse=True)

    return merged[:k]


def main():

    query = input("Enter bug description: ")

    candidates = retrieve_candidates(query, top_n=50)

    results = rerank(query, candidates, k=5)

    print("\nTop similar code (reranked):\n")

    for r in results:

        print("-----")
        print("RerankScore:", r["rerank_score"], "| FaissScore:", r["faiss_score"])
        print(r["chunk"][:500])


if __name__ == "__main__":
    main()