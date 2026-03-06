import json
import os
from datetime import datetime


FEEDBACK_FILE = "datasets/learn/bug_fix_pairs.jsonl"


def store_bug_fix_pair(bug_id, query, result):

    os.makedirs("datasets/learn", exist_ok=True)

    record = {
        "bug_id": bug_id,
        "timestamp": datetime.utcnow().isoformat(),
        "buggy_code": query,
        "generated_fix": result.get("corrected_function"),
        "explanation": result.get("explanation")
    }

    with open(FEEDBACK_FILE, "a", encoding="utf8") as f:
        f.write(json.dumps(record) + "\n")