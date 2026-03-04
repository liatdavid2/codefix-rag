import json
import faiss
from sentence_transformers import SentenceTransformer

INDEX_DIR = "datasets/index"

model = SentenceTransformer("all-MiniLM-L6-v2")


def load_index():

    index = faiss.read_index(f"{INDEX_DIR}/code.index")

    with open(f"{INDEX_DIR}/chunks.json", "r", encoding="utf8") as f:
        chunks = json.load(f)

    return index, chunks


def search_code(query, k=5):

    index, chunks = load_index()

    query_embedding = model.encode([query])

    distances, indices = index.search(query_embedding, k)

    results = []

    for score, idx in zip(distances[0], indices[0]):
        results.append((score, chunks[idx]))

    return results


def main():

    query = input("Enter bug description: ")

    results = search_code(query)

    print("\nTop similar code:\n")

    for score, code in results:
        print("-----")
        print("Score:", score)
        print(code[:400])


if __name__ == "__main__":
    main()