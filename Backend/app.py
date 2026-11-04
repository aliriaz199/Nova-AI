
from flask import Flask, request, jsonify, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from google import genai
from google.genai import types
from dotenv import load_dotenv
from pathlib import Path
import os
import traceback
import httpx

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

app = Flask(__name__, static_folder=None)

# Maximum incoming request size: 1 MB
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024

# Rate limiting: 10 requests per minute per IP
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://"
)

# Gemini API configuration
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
    return send_from_directory(BASE_DIR / "public", "index.html")


@app.route("/chat", methods=["POST"])
@limiter.limit("10 per minute")
def chat():

    # Check API key
    if client is None:
        return jsonify({
            "error": "AI service is not configured."
        }), 500

    # Read request data
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "Invalid request data."
        }), 400

    message = data.get("message", "")
    history = data.get("history", [])

    # Validate message
    if not isinstance(message, str):
        return jsonify({
            "error": "Message must be text."
        }), 400

    message = message.strip()

    if not message:
        return jsonify({
            "error": "Please enter a message."
        }), 400

    if len(message) > 10000:
        return jsonify({
            "error": "Message is too long."
        }), 400

    # Validate conversation history
    if not isinstance(history, list):
        return jsonify({
            "error": "Invalid conversation history."
        }), 400

    if len(history) > 20:
        return jsonify({
            "error": "Conversation history is too long."
        }), 400

    # Prepare validated conversation history
    contents = []

    for item in history:

        if not isinstance(item, dict):
            continue

        role = item.get("role")
        text = item.get("text", "")

        if (
            role in ["user", "model"]
            and isinstance(text, str)
            and text.strip()
            and len(text) <= 10000
        ):
            contents.append({
                "role": role,
                "parts": [{"text": text.strip()}]
            })

    # Add latest user message
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

        if not response.text:
            return jsonify({
                "error": "The AI could not generate a response."
            }), 502

        return jsonify({
            "reply": response.text
        })

    except Exception:

        print("\n========== GEMINI ERROR ==========", flush=True)
        traceback.print_exc()
        print("==================================", flush=True)

        return jsonify({
            "error": "Something went wrong. Please try again."
        }), 500


# Handle oversized requests
@app.errorhandler(413)
def request_too_large(error):
    return jsonify({
        "error": "Request is too large."
    }), 413


# Handle rate limit errors
@app.errorhandler(429)
def rate_limit_exceeded(error):
    return jsonify({
        "error": "Too many requests. Please wait a minute and try again."
    }), 429


if __name__ == "__main__":
    app.run(debug=True)
