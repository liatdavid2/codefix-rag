import subprocess
from pathlib import Path


def get_fix_patch(repo_path, buggy_commit, fixed_commit):

    try:

        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_path),
                "diff",
                buggy_commit,
                fixed_commit
            ],
            capture_output=True,
            text=True
        )

        return result.stdout

    except Exception:
        return ""