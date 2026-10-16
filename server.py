import argparse
import threading
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory, stream_with_context

from vortex.engine import Vortex

ROOT = Path(__file__).parent
WEB = ROOT / "web"

app = Flask(__name__, static_folder=None)
lock = threading.Lock()
engine = None


def load_engine(checkpoint_dir):
    global engine
    engine = Vortex(checkpoint_dir)


def clean_history(raw):
    history = []
    for item in raw[-20:]:
        role = item.get("role")
        content = str(item.get("content", "")).strip()[:1000]
        if role in ("user", "bot") and content:
            history.append((role, content))
    return history


@app.get("/")
def index():
    return send_from_directory(WEB, "index.html")


@app.get("/<path:name>")
def static_files(name):
    return send_from_directory(WEB, name)


@app.get("/api/info")
def info():
    return jsonify({
        "name": "Vortex",
        "params": engine.model.num_params(),
        "vocab": engine.tokenizer.vocab_size,
        "context": engine.config.block_size,
        "device": engine.device,
    })


@app.post("/api/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    history = clean_history(payload.get("history", []))
    if not history or history[-1][0] != "user":
        return jsonify({"error": "history must end with a user message"}), 400
    temperature = float(payload.get("temperature", 0.7))
    temperature = max(0.0, min(temperature, 2.0))

    def generate():
        with lock:
            for piece in engine.stream(history, temperature=temperature):
                yield piece

    return Response(stream_with_context(generate()), mimetype="text/plain; charset=utf-8")


def main():
    parser = argparse.ArgumentParser(description="Vortex web server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--checkpoint-dir", default=str(ROOT / "checkpoints"))
    args = parser.parse_args()
    load_engine(args.checkpoint_dir)
    print(f"Vortex running at http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, threaded=True)


if __name__ == "__main__":
    main()
