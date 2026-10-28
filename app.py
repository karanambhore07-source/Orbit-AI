import logging
import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory

from chatbot import (
    MAX_HISTORY_MESSAGES,
    MODEL_DIR,
    format_report,
    generate_hosted_response,
    generate_response,
    hosted_ai_is_configured,
)


app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024
logging.basicConfig(level=logging.INFO)

MAX_MESSAGE_LENGTH = 4000


def model_files_available() -> bool:
    model_dir = Path(MODEL_DIR)
    has_weights = any(
        (model_dir / name).is_file()
        for name in (
            "model.safetensors",
            "pytorch_model.bin",
            "model.safetensors.index.json",
            "pytorch_model.bin.index.json",
        )
    )
    return (model_dir / "config.json").is_file() and has_weights


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/static/<path:filename>")
def static_asset(filename: str):
    return send_from_directory(Path(__file__).resolve().parent / "public" / "static", filename)


@app.get("/api/status")
def status():
    local_model_available = model_files_available()
    hosted_ai_available = hosted_ai_is_configured()
    vercel_deployment = bool(os.environ.get("VERCEL"))
    return jsonify(
        {
            "model_available": local_model_available,
            "hosted_ai_available": hosted_ai_available,
            "ai_available": local_model_available or hosted_ai_available,
            "hosting_mode": "vercel" if vercel_deployment else "local",
            "model_name": (
                "SmolLM2-360M-Instruct"
                if local_model_available
                else os.environ.get("AI_MODEL", "Hosted AI")
            ),
            "max_history_messages": MAX_HISTORY_MESSAGES,
        }
    )


@app.post("/api/chat")
def chat():
    payload = request.get_json()
    if not isinstance(payload, dict):
        return jsonify({"error": "Send a JSON object with a message."}), 400

    message = payload.get("message")
    if not isinstance(message, str) or not message.strip():
        return jsonify({"error": "Enter a message before sending."}), 400
    if len(message) > MAX_MESSAGE_LENGTH:
        return jsonify({"error": f"Messages must be {MAX_MESSAGE_LENGTH} characters or fewer."}), 400

    history = payload.get("history", [])
    if not isinstance(history, list) or len(history) > MAX_HISTORY_MESSAGES:
        return jsonify({"error": "Conversation history is invalid. Start a new chat and try again."}), 400
    for item in history:
        if (
            not isinstance(item, dict)
            or item.get("role") not in {"user", "assistant"}
            or not isinstance(item.get("content"), str)
        ):
            return jsonify({"error": "Conversation history is invalid. Start a new chat and try again."}), 400

    try:
        if message.strip().lower().startswith("/report"):
            answer = format_report(message.strip())
        elif model_files_available():
            answer = generate_response(message.strip(), history)
        elif hosted_ai_is_configured():
            answer = generate_hosted_response(message.strip(), history)
        else:
            if os.environ.get("VERCEL"):
                return (
                    jsonify(
                        {
                            "error": "Hosted AI is not configured. Add AI_API_KEY, AI_BASE_URL, and AI_MODEL in your Vercel project settings."
                        }
                    ),
                    503,
                )
            return (
                jsonify(
                    {
                        "error": "The local AI model is not installed yet. Run `python download_model.py`, then restart the app."
                    }
                ),
                503,
            )
    except Exception:
        app.logger.exception("AI provider failed to generate a response")
        return jsonify({"error": "The AI provider could not generate a response. Check the server logs and provider configuration."}), 502

    return jsonify({"answer": answer})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
