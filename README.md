# CodeFix-RAG: Retrieval-Augmented Bug Fixing for Python

This project implements a **Code RAG system** that detects and fixes bugs in Python code using:

* semantic code retrieval
* vector search (FAISS)
* reranking
* LLM-based code repair

The system receives a **buggy code snippet**, retrieves similar code from a repository index, reranks the results, and uses an LLM to generate a **diff patch and corrected function**.

---

# System Architecture

The system contains two pipelines:

1. **Offline pipeline** – builds the vector index
2. **Online pipeline** – retrieves similar code and generates fixes

---

# Offline Pipeline (Index Creation)

The offline stage processes source code repositories and builds the FAISS index used for retrieval.

```
Source Code Repositories
        │
        ▼
Code Extraction
(parse Python files)
        │
        ▼
Code Chunking
(function-level chunks)
        │
        ▼
Embedding Model
BAAI/bge-small-en
        │
        ▼
Vector Embeddings
        │
        ▼
FAISS Index
(code.index)
        │
        ▼
Metadata Storage
(chunks.json)
```

Artifacts produced:

```
datasets/index/code.index
datasets/index/chunks.json
```

`chunks.json` stores metadata for each code chunk.

Example structure:

```
{
  "code": "def foo(): ...",
  "path": "repo/file.py"
}
```

---

# Online Pipeline (Bug Detection and Fix)

At runtime the system receives buggy code and performs retrieval + generation.

```
User Input (Buggy Code)
        │
        ▼
Code Embedding
BAAI/bge-small-en
        │
        ▼
Vector Search
FAISS index
(top-N candidates)
        │
        ▼
Reranking
CrossEncoder
(ms-marco-MiniLM-L-6-v2)
        │
        ▼
Top-K Code Examples
        │
        ▼
Prompt Construction
(context + code)
        │
        ▼
LLM Generation
(OpenAI GPT-4o-mini)
        │
        ▼
Output
• Explanation
• Git Diff Patch
• Corrected Function
```

---

# Retrieval Model

The embedding model converts code into vector representations.

Model used:

```
BAAI/bge-small-en
```

This model is optimized for semantic retrieval.

Query preprocessing improves results:

```
query = "Find similar buggy Python code:\n" + query
```

This helps the embedding model understand the search intent.

---

# Vector Search

Vector search is implemented using **FAISS**.

FAISS performs approximate nearest neighbor search in the embedding space.

Steps:

1. embed query code
2. search nearest vectors
3. return top-N similar code snippets

Example call:

```
index.search(query_embedding, top_n)
```

---

# Reranking

Initial vector search may return noisy results.

To improve accuracy the system uses a **CrossEncoder reranker**.

Model:

```
cross-encoder/ms-marco-MiniLM-L-6-v2
```

The reranker evaluates pairs:

```
(query_code, candidate_code)
```

Unlike embeddings, the CrossEncoder processes both inputs jointly and produces a relevance score.

Pipeline:

```
FAISS top-50 results
        │
        ▼
CrossEncoder scoring
        │
        ▼
Sorted results
        │
        ▼
Top-5 candidates
```

This improves the quality of the context provided to the LLM.

---

# LLM Generation

The final stage uses an LLM to analyze the code and generate a fix.

Model used:

```
GPT-4o-mini
```

The LLM receives:

* buggy code
* retrieved code examples

The model outputs structured JSON:

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

Git Diff Patch

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

Corrected Function

```
def get_item(lst, index):
    if index < 0 or index >= len(lst):
        raise IndexError("Index out of bounds")
    return lst[index]
```

---

# Running the System

Activate environment:

```
pip install -r requirements.txt
```

Run:

```
python -m generate.generate_fix
```

Paste buggy code and finish with:

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

# Input Handling Issue (Windows CMD)

While developing the system several input issues occurred.

### Problem 1

Using only `Enter` to finish input caused **partial code capture** in Windows CMD.

The input loop stopped early and truncated the code snippet.

### Problem 2

Using

```
Ctrl + Z
```

to terminate input did not behave reliably in CMD.

Sometimes the process stalled waiting for EOF.

### Final Solution

A custom termination token was implemented:

```
END
```

Input example:

```
def foo():
    return 1
END
```

This approach proved stable across Windows terminals.

---

# Key Design Decisions

### Why Retrieval Augmentation

LLMs alone may hallucinate fixes.

Retrieval provides:

* real code examples
* grounding
* better repair suggestions

### Why FAISS

FAISS provides fast similarity search for large code corpora.

### Why Reranking

Vector search retrieves semantically similar code but may include noise.

The CrossEncoder reranker improves ranking accuracy.

### Why Structured JSON Output

Returning strict JSON allows reliable parsing and downstream automation.

---
# Example Input / Output

## Example Run

```bash
python -m generate.generate_fix
```

## Input

The user pastes buggy Python code and finishes with `END`.

```
Paste buggy code. Type END on a new line when finished:

def get_item(lst, index):
    return lst[index]

data = [1,2,3]
print(get_item(data, 10))
END
```

---

# System Processing

The system loads the retrieval and reranking components:

```
Loading embedding model...
Loading FAISS index...
Loading reranker model...
```

It then retrieves similar code snippets from the indexed repositories.

---

# Retrieved Code Examples

```
Top retrieved code snippets:

[1] File: unknown_file.py  score=4.149101257324219

File: datasets/repos/scrapy/scrapy/commands/parse.py
Object: print_items
Type: FunctionDef

    def print_items(self, lvl: int | None = None, colour: bool = True) -> None:
        if lvl is None:
            items = [item for lst in self.items.values() for item in lst]
        else:
```

```
[2] File: unknown_file.py  score=2.5646955966949463

d.addCallback(self.iterate_spider_output)
return d
if inspect.iscoroutine(result):
    d = deferred_from_coro(result)
```

```
[3] File: unknown_file.py  score=0.8291720747947693

def get_help(self) -> str:
    b = []
    b.append("Available Scrapy objects:")
```

The retrieved examples are used as context for the LLM.

---

# Model Output

## Explanation

```
The bug in the provided code occurs when an invalid index is accessed in the list,
which raises an IndexError. This can be fixed by adding error handling to manage
out-of-bounds index access.
```

---

# Git Diff Patch

```diff
--- original.py
+++ fixed.py
@@ -1,3 +1,7 @@
 def get_item(lst, index):
-    return lst[index]
+    try:
+        return lst[index]
+    except IndexError:
+        return None
```

---

# Corrected Function

```python
def get_item(lst, index):
    try:
        return lst[index]
    except IndexError:
        return None
```

---
