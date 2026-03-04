import json
import faiss
from sentence_transformers import SentenceTransformer


INDEX_DIR = "datasets/index"


def load_index():

    index = faiss.read_index(f"{INDEX_DIR}/code.index")

    with open(f"{INDEX_DIR}/chunks.json", "r", encoding="utf8") as f:
        chunks = json.load(f)

    return index, chunks


def search_code(query, k=5):

    index, chunks = load_index()

    model = SentenceTransformer("all-MiniLM-L6-v2")

    query_embedding = model.encode([query])

    distances, indices = index.search(query_embedding, k)

    results = []

    for idx in indices[0]:
        results.append(chunks[idx])

    return results


def main():

    query = input("Enter bug description: ")

    results = search_code(query)

    print("\nTop similar code:\n")

    for r in results:
        print("-----")
        print(r[:400])


if __name__ == "__main__":
    main()