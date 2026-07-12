from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import os
import requests
import markdown

load_dotenv()

app = Flask(__name__)

API_KEY = os.getenv("GEMINI_API_KEY")

URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/review", methods=["POST"])
def review():
    data = request.get_json()
    code = data.get("code", "")

    prompt = f"""
You are an expert software engineer.

Review the following code.

Return your response in this format:

## Bugs
## Improvements
## Best Practices
## Optimized Code
## Rating out of 10

Code:

{code}
"""

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }

    headers = {
        "Content-Type": "application/json"
    }

    response = requests.post(URL, headers=headers, json=payload)

    if response.status_code != 200:
        return jsonify({
            "result": f"API Error:<br><br>{response.text}"
        })

    result = response.json()

    text = result["candidates"][0]["content"]["parts"][0]["text"]

    html = markdown.markdown(text)

    return jsonify({"result": html})


if __name__ == "__main__":
    app.run(debug=True)