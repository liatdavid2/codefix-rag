# CodeFix-RAG

### Retrieval-Augmented Bug Fixing for Python

CodeFix-RAG is a system that detects and fixes Python bugs using a **Retrieval-Augmented Generation (RAG)** pipeline.

The system combines:

* semantic code retrieval
* vector similarity search (FAISS)
* neural reranking
* LLM-based code repair

Given a **buggy Python snippet**, the system retrieves similar code examples from indexed repositories and uses them as context for an LLM that generates:

* bug explanation
* Git diff patch
* corrected function

---

# Key Features

Semantic Code Search
Uses vector embeddings to retrieve semantically similar Python code.

Reranked Retrieval
Improves retrieval accuracy using a CrossEncoder neural reranker.

LLM-Based Code Repair
Generates fixes and explanations grounded in retrieved examples.

Structured Output
Returns fixes as structured JSON including explanation, patch, and corrected code.

---

# System Architecture

CodeFix-RAG consists of two main pipelines:

1. **Offline pipeline** – builds the vector index from source code  
2. **Online pipeline** – retrieves similar code and generates bug fixes

OFFLINE PIPELINE
────────────────────────────────

Open Source Repositories
          │
          ▼
   Python Code Parsing
          │
          ▼
   Function Extraction
          │
          ▼
      Code Chunking
          │
          ▼
 Embedding Model (BGE)
          │
          ▼
     Vector Embeddings
          │
          ▼
        FAISS Index
      + chunks.json


ONLINE PIPELINE
────────────────────────────────

Buggy Python Code
      (User Input)
          │
          ▼
     Code Embedding
          │
          ▼
      FAISS Search
      (Top-N code)
          │
          ▼
 CrossEncoder Reranker
          │
          ▼
   Top-K Code Snippets
          │
          ▼
     Prompt Builder
          │
          ▼
     LLM (GPT-4o-mini)
          │
          ▼
 Explanation + Diff + Fix

---

# Retrieval Model

Embedding model used:

```
BAAI/bge-small-en
```

This model converts code into semantic vectors enabling similarity search across codebases.

Query preprocessing improves retrieval quality:

```
query = "Find similar buggy Python code:\n" + query
```

---

# Vector Search

Vector search is implemented using **FAISS**.

FAISS performs approximate nearest neighbor search across high-dimensional embedding spaces.

Steps:

1. Embed query code
2. Search nearest vectors
3. Return top-N similar code snippets

Example:

```
index.search(query_embedding, top_n)
```

---

# Reranking

Initial vector search may return noisy results.

The system applies a neural **CrossEncoder reranker** to improve ranking accuracy.

Model used:

```
cross-encoder/ms-marco-MiniLM-L-6-v2
```

The reranker evaluates:

```
(query_code, candidate_code)
```

and assigns a relevance score.

Pipeline:

```
FAISS Top-50
      │
      ▼
CrossEncoder Scoring
      │
      ▼
Sorted Results
      │
      ▼
Top-5 Context Snippets
```

---

# LLM Generation

The final stage uses an LLM to generate the bug explanation and fix.

Model:

```
GPT-4o-mini
```

The model receives:

* buggy code
* retrieved code snippets

Output format:

```
{
  "explanation": "...",
  "diff": "...",
  "corrected_function": "..."
}
```

Example output:

Explanation

```
The bug occurs because the code accesses a list index that may be out of range.
```

Diff patch

```
--- original.py
+++ fixed.py
@@ -1,3 +1,7 @@
 def get_item(lst, index):
-    return lst[index]
+    if index < 0 or index >= len(lst):
+        raise IndexError("Index out of bounds")
+    return lst[index]
```

Corrected function

```
def get_item(lst, index):
    if index < 0 or index >= len(lst):
        raise IndexError("Index out of bounds")
    return lst[index]
```

---

# Dataset: BugsInPy

BugsInPy is a benchmark dataset containing real bugs collected from open-source Python projects.

Each bug includes:

* buggy version of the code
* fixed version
* tests that reproduce the bug

Example metadata entry:

```
{
  "bug_id": "pandas_82",
  "project": "pandas",
  "buggy_commit": "6f395ad",
  "fixed_commit": "e83a6bddac8c89b144dfe0783594dd332c5b3030",
  "test_file": "pandas/tests/reshape/merge/test_merge.py"
}
```

---

# Running the System

Install dependencies:

```
pip install -r requirements.txt
```

Run the system:

```
python -m generate.generate_fix
```

Paste buggy Python code and terminate input with:

```
END
```

Example:

```
def get_item(lst, index):
    return lst[index]

data = [1,2,3]
print(get_item(data, 10))
END
```

---

# Project Structure

```
codefix-rag
│
├── datasets                       # Data used for retrieval index
│   ├── raw/BugsInPy               # BugsInPy dataset
│   ├── processed                  # Processed dataset metadata
│   └── repos                      # Cloned Python repositories
│
├── ingest
│   └── ingest_bugsinpy.py         # Processes BugsInPy metadata
│
├── retrieve
│   ├── build_index.py             # Builds FAISS vector index
│   └── retrieve_similar_code.py   # Retrieval and reranking pipeline
│
├── generate
│   └── generate_fix.py            # Online bug fixing pipeline
│
├── requirements.txt
├── Dockerfile
└── README.md
```

---

# Design Choices

Retrieval-Augmented Generation
Reduces hallucinations by grounding the LLM in real code examples.

Vector Search with FAISS
Enables scalable semantic search across large codebases.

Neural Reranking
Improves relevance of retrieved code snippets.

Structured JSON Output
Ensures reliable parsing and downstream automation.

---

# Future Improvements

Possible extensions:

* AST-based bug detection
* hybrid retrieval (BM25 + vector search)
* indexing buggy/fixed code pairs
* training embeddings specifically for code repair

---