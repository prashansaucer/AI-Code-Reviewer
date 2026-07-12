from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv
import markdown
import os
import requests
import time

load_dotenv()

app = Flask(__name__)

API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash").strip()
MAX_CODE_LENGTH = 40000
REQUEST_TIMEOUT = 120

if not API_KEY:
    raise ValueError(
        "GEMINI_API_KEY is missing. Create a .env file and add your API key."
    )

API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    f"models/{MODEL}:generateContent"
)

SYSTEM_PROMPT = """
You are a senior software engineer, debugger and code optimization specialist.

Your goal is to return accurate, complete, executable and optimized code.

Rules:
1. Detect the programming language automatically.
2. Understand the code's purpose before changing it.
3. Report only issues supported by the supplied code.
4. Do not invent bugs, missing files or requirements.
5. Preserve the intended functionality.
6. Fix confirmed syntax, logic, runtime, security and performance issues.
7. Keep the solution simple and readable.
8. Avoid unnecessary dependencies.
9. Include every required import.
10. Keep the same programming language.
11. Never return pseudocode or placeholders.
12. Never omit unchanged but necessary code.
13. Clearly state anything that cannot be verified from the snippet.
14. Do not claim that the code was executed.
15. Mentally verify syntax and logical consistency before responding.
"""


def build_prompt(code: str, mode: str) -> str:
    modes = {
        "quick": (
            "Focus on definite bugs and the most important corrections. "
            "Keep the explanation concise."
        ),
        "detailed": (
            "Review correctness, readability, security, performance, "
            "maintainability, validation and relevant edge cases."
        ),
        "security": (
            "Focus on unsafe input, injection, exposed secrets, authentication, "
            "authorization, data leakage and insecure operations."
        ),
        "performance": (
            "Focus on algorithm efficiency, memory usage, repeated work, "
            "blocking operations and scalability."
        ),
    }

    instruction = modes.get(mode, modes["detailed"])

    return f"""
Review the following code.

Review mode:
{instruction}

Return exactly these sections:

## Code Summary
Briefly explain what the code does.

## Language Detected
Return the detected programming language.

## Confirmed Bugs
List only definite bugs.

For every bug provide:
- Location
- Problem
- Impact
- Fix

Write "No confirmed bugs found." when appropriate.

## Improvements
List the most useful improvements for correctness, security,
performance, readability and maintainability.

## Correct and Optimized Code
Return one complete executable fenced code block.

The optimized code must:
- preserve intended functionality;
- fix all confirmed bugs;
- include all required imports;
- handle relevant edge cases;
- avoid unnecessary dependencies;
- contain no placeholders or pseudocode;
- remain in the same programming language.

## Test Cases
Provide a few practical test cases with expected results.

## Rating
Give scores out of 10 for:
- Correctness
- Readability
- Security
- Performance
- Maintainability
- Overall

Code:
```text
{code}
```
"""


def build_retry_prompt(code: str) -> str:
    return f"""
Correct and optimize the following code.

Return exactly:

## Language Detected

## Correct and Optimized Code

Provide one complete executable fenced code block.

Rules:
- Keep the same programming language.
- Preserve intended functionality.
- Fix syntax and logical errors.
- Include all required imports.
- Avoid unnecessary dependencies.
- Do not use placeholders or pseudocode.

Code:
```text
{code}
```
"""


def create_payload(prompt: str, max_tokens: int = 4096) -> dict:
    return {
        "systemInstruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": {
            "temperature": 0.15,
            "topP": 0.85,
            "maxOutputTokens": max_tokens,
        },
    }


def api_headers() -> dict:
    return {
        "Content-Type": "application/json",
        "x-goog-api-key": API_KEY,
    }


def send_to_gemini(prompt: str, max_tokens: int = 4096) -> dict:
    response = requests.post(
        API_URL,
        headers=api_headers(),
        json=create_payload(prompt, max_tokens),
        timeout=REQUEST_TIMEOUT,
    )

    try:
        result = response.json()
    except ValueError as error:
        raise ValueError("Gemini returned an invalid JSON response.") from error

    if not response.ok:
        message = result.get("error", {}).get(
            "message",
            "The Gemini API request failed.",
        )
        raise ValueError(message)

    return result


def extract_text(result: dict) -> tuple[str, str]:
    candidates = result.get("candidates", [])

    if not candidates:
        reason = result.get("promptFeedback", {}).get(
            "blockReason",
            "No response was generated.",
        )
        raise ValueError(reason)

    candidate = candidates[0]
    finish_reason = candidate.get("finishReason", "UNKNOWN")

    parts = candidate.get("content", {}).get("parts", [])
    text = "".join(
        part.get("text", "")
        for part in parts
        if part.get("text")
    ).strip()

    if not text:
        raise ValueError(
            f"Empty response. Finish reason: {finish_reason}"
        )

    return text, finish_reason


def generate_review(code: str, mode: str) -> tuple[str, str]:
    result = send_to_gemini(build_prompt(code, mode))
    try:
        return extract_text(result)
    except ValueError as error:
        if "MALFORMED_RESPONSE" not in str(error).upper():
            raise

    time.sleep(1)

    retry_result = send_to_gemini(
        build_retry_prompt(code),
        max_tokens=3072,
    )
    return extract_text(retry_result)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "model": MODEL,
    })


@app.route("/review", methods=["POST"])
def review():
    data = request.get_json(silent=True) or {}

    code = str(data.get("code", "")).strip()
    mode = str(data.get("mode", "detailed")).lower().strip()

    if not code:
        return jsonify({
            "error": "Please enter some code."
        }), 400

    if len(code) > MAX_CODE_LENGTH:
        return jsonify({
            "error": (
                "The submitted code is too large. "
                "Please submit a smaller file or section."
            )
        }), 400

    try:
        text, finish_reason = generate_review(code, mode)

        html = markdown.markdown(
            text,
            extensions=[
                "fenced_code",
                "tables",
                "sane_lists",
            ],
        )

        return jsonify({
            "result": html,
            "markdown": text,
            "finish_reason": finish_reason,
            "model": MODEL,
        })

    except requests.Timeout:
        return jsonify({
            "error": (
                "The Gemini request timed out. "
                "Try reviewing a shorter code sample."
            )
        }), 504

    except requests.RequestException as error:
        app.logger.exception("Gemini network error")
        return jsonify({
            "error": f"Network error: {error}"
        }), 502

    except ValueError as error:
        return jsonify({
            "error": str(error)
        }), 400

    except Exception:
        app.logger.exception("Unexpected code-review error")
        return jsonify({
            "error": "An unexpected server error occurred."
        }), 500


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
    )