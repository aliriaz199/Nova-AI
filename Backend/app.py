
from flask import Flask, request, jsonify, send_from_directory
from google import genai
from google.genai import types
from dotenv import load_dotenv
from pathlib import Path
import os
import traceback
import httpx

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

app = Flask(
    __name__,
    static_folder=str(BASE_DIR / "Frontend"),
    static_url_path=""
)

api_key = os.getenv("GEMINI_API_KEY")

http_client = httpx.Client(
    transport=httpx.HTTPTransport(local_address="0.0.0.0"),
    timeout=60.0
)

client = genai.Client(
    api_key=api_key,
    http_options=types.HttpOptions(httpx_client=http_client)
) if api_key else None


@app.route("/")
def home():
    return send_from_directory(BASE_DIR / "Frontend", "index.html")


@app.route("/chat", methods=["POST"])
def chat():

    if client is None:
        return jsonify({"error": "Gemini API key is missing."}), 500

    data = request.get_json()
    message = data.get("message", "").strip() if data else ""
    history = data.get("history", []) if data else []

    if not message:
        return jsonify({"error": "Please enter a message."}), 400

    # Prepare conversation history for Gemini
    contents = []

    for item in history:
        role = item.get("role")
        text = item.get("text", "").strip()

        if role in ["user", "model"] and text:
            contents.append({
                "role": role,
                "parts": [{"text": text}]
            })

    # Add the latest user message
    contents.append({
        "role": "user",
        "parts": [{"text": message}]
    })

    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction="""
                You are Nova AI, a helpful and friendly AI assistant.

                Your name is Nova AI.
                Never identify yourself as Google Gemini
                or a Google assistant.

                If someone asks who you are,
                say you are Nova AI.

                Answer users clearly and helpfully.
                """
            )
        )

        return jsonify({"reply": response.text})

    except Exception as e:
        print("\n========== GEMINI ERROR ==========", flush=True)
        traceback.print_exc()
        print("==================================", flush=True)

        return jsonify({
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(debug=True)
