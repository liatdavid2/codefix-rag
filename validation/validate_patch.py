import ast
import subprocess
import tempfile
import os


def validate_syntax(code: str) -> bool:
    """
    Check if generated Python code has valid syntax.
    """
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def validate_compile(code: str) -> bool:
    """
    Check if code compiles with Python interpreter.
    """
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as f:
            f.write(code.encode())
            temp_path = f.name

        subprocess.check_output(
            ["python", "-m", "py_compile", temp_path],
            stderr=subprocess.STDOUT
        )

        os.remove(temp_path)

        return True

    except subprocess.CalledProcessError:
        return False


def validate_lint(code: str) -> bool:
    """
    Optional static analysis using ruff.
    """
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as f:
            f.write(code.encode())
            temp_path = f.name

        result = subprocess.run(
            ["ruff", "check", temp_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )

        os.remove(temp_path)

        return result.returncode == 0

    except Exception:
        return False


def compute_confidence(rerank_score: float, syntax_ok: bool, compile_ok: bool):
    """
    Simple confidence scoring.
    """
    score = rerank_score

    if syntax_ok:
        score += 0.2

    if compile_ok:
        score += 0.2

    return score


def validate_fix(code: str, rerank_score: float):
    """
    Run full validation pipeline.
    """

    syntax_ok = validate_syntax(code)

    compile_ok = False
    lint_ok = False

    if syntax_ok:
        compile_ok = validate_compile(code)

    if compile_ok:
        lint_ok = validate_lint(code)

    confidence = compute_confidence(
        rerank_score,
        syntax_ok,
        compile_ok
    )

    return {
        "syntax_ok": syntax_ok,
        "compile_ok": compile_ok,
        "lint_ok": lint_ok,
        "confidence": confidence
    }