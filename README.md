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
Below is a **clean English version suitable for a README**. I kept it professional and structured so it looks good in a portfolio project.

---

# What Happens in the Pipeline

## 1. User Input

The system receives buggy code from the user:

```python
def get_item(lst, index):
    return lst[index]

data = [1,2,3]
print(get_item(data, 10))
```

Problem:

`10` is outside the bounds of the list, which raises an `IndexError`.

---

# Step 1 — Retrieval

The system searches for similar code patterns in the indexed codebase using **FAISS vector search**.

During execution the system loads the necessary components:

```
Loading embedding model...
Loading FAISS index...
Loading reranker model...
```

It then retrieves relevant code snippets:

```
Top retrieved code snippets
```

Example:

```
datasets/repos/scrapy/scrapy/commands/parse.py
```

This means the system found code with **similar structural patterns** in the Scrapy repository.

This retrieval approach is similar to techniques used in systems such as:

* GitHub Copilot
* Sourcegraph Cody
* DeepMind AlphaCode

---

# Step 2 — Reranking

The retrieved results are reranked using a **CrossEncoder model**:

```
cross-encoder/ms-marco-MiniLM-L-6-v2
```

The reranker evaluates the relevance between the query and the retrieved code.

Example scores:

```
score = 4.14
score = 2.56
score = 0.82
```

Higher scores indicate more relevant code snippets.
The first result is considered the most relevant.

---

# Step 3 — Generation (LLM)

The LLM receives two inputs:

* The **buggy code**
* The **retrieved relevant code snippets**

Using this context, the model generates both an **explanation** and a **patch**.

Explanation example:

```
The bug occurs when an index that is out of range is accessed.
```

Generated patch:

```diff
--- original.py
+++ fixed.py
@@ -1,4 +1,6 @@
 def get_item(lst, index):
-    return lst[index]
+    if index < 0 or index >= len(lst):
+        raise IndexError('Index out of range')
+    return lst[index]
```

This is a **real Git-style patch format**, which is commonly used in bug-fixing workflows.

---

# Step 4 — Corrected Function

The system also outputs the corrected version of the function:

```python
def get_item(lst, index):
    if index < 0 or index >= len(lst):
        raise IndexError('Index out of range')
    return lst[index]
```

---

# Step 5 — Validation

The system performs automatic validation of the generated fix:

```
{'syntax_ok': True, 'compile_ok': True, 'lint_ok': False, 'confidence': 0.4}
```

Meaning:

| Check      | Result                         |
| ---------- | ------------------------------ |
| syntax_ok  | The code syntax is valid       |
| compile_ok | The code compiles successfully |
| lint_ok    | Style issues detected          |
| confidence | Low confidence score           |

---

# Why `lint_ok = False`

This likely happens due to **PEP8 formatting issues**.

Example:

```python
data = [1,2,3]
```

PEP8 formatting recommends:

```python
data = [1, 2, 3]
```

Another possible reason:

```python
raise IndexError('Index out of range')
```

However, these are **style issues only** and do not affect functionality.

---

If you want, I can also give you a **very strong README section called "System Architecture" with a diagram** that will make this project look much more impressive in interviews.

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

```
OFFLINE PIPELINE

Open Source Python Repositories
            |
            v
      Python Code Parsing
            |
            v
      Function Extraction
            |
            v
         Code Chunking
            |
            v
   Embedding Model (BGE-small)
            |
            v
       Vector Embeddings
            |
            v
          FAISS Index
         + chunks.json



ONLINE PIPELINE

Buggy Python Code (User Input)
            |
            v
        Code Embedding
            |
            v
        FAISS Retrieval
        (Top-N Results)
            |
            v
     CrossEncoder Reranker
            |
            v
       Top-K Code Snippets
            |
            v
        Prompt Builder
            |
            v
        LLM (GPT-4o-mini)
            |
            v
   Explanation + Diff Patch + Fix
```
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

## Example: Bug Fix Generation

Below is an example of running the system on a small Python bug.

### Input

User provides buggy code:

```python
def call_method(obj, name):
    method = getattr(obj, name)
    return method()

print(call_method({}, "run"))
```

This code raises an error because the object (`dict`) does not have a method named `"run"`.

---

### Retrieval Stage

The system retrieves similar code patterns from the indexed repository.

Top retrieved snippets:

```
File: scrapy/utils/request.py
Object: _get_method

def _get_method(obj: Any, name: Any) -> Any:
    name = str(name)
    try:
        return getattr(obj, name)
```

This example contains a similar pattern using `getattr`, which helps the model understand how attribute access is handled in real code.

---

### Generated Explanation

```
The bug occurs because the method being called may not exist on the given object,
leading to an AttributeError. The code should check if the method exists before
attempting to call it.
```

---

### Generated Patch

```diff
--- original.py
+++ corrected.py
@@
 def call_method(obj, name):
-    method = getattr(obj, name)
-    return method()
+    if hasattr(obj, name):
+        return getattr(obj, name)()
+    raise ValueError(f'Method {name!r} not found in: {obj}')
```

---

### Corrected Function

```python
def call_method(obj, name):
    if hasattr(obj, name):
        return getattr(obj, name)()
    raise ValueError(f'Method {name!r} not found in: {obj}')
```

---

### Validation

The generated patch is validated automatically:

```
{
  "syntax_ok": True,
  "compile_ok": True,
  "lint_ok": False,
  "confidence": 0.4
}
```

Validation checks include:

* syntax validation
* compilation check
* lint analysis
* confidence estimation based on retrieval score

---

### Pipeline

The system pipeline:

```
Buggy Code
   ↓
Sandbox Execution (detect exception)
   ↓
Embedding Generation
   ↓
FAISS Vector Retrieval
   ↓
CrossEncoder Reranking
   ↓
LLM Patch Generation
   ↓
Patch Validation
```

---


