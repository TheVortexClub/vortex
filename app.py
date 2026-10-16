import socket
import sys
import threading
import webbrowser
from pathlib import Path

from werkzeug.serving import make_server

import server

APP_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent


def find_checkpoint_dir():
    for candidate in (APP_DIR / "checkpoints", server.ROOT / "checkpoints"):
        if (candidate / "vortex.pt").exists() and (candidate / "tokenizer.json").exists():
            return candidate
    return None


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def show_error(message):
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, message, "Vortex", 0x10)
    except Exception:
        sys.stderr.write(message + "\n")


def main():
    checkpoint_dir = find_checkpoint_dir()
    if checkpoint_dir is None:
        show_error("No trained model found.\n\nRun \"python train.py\" first, or place a checkpoints folder next to Vortex.")
        sys.exit(1)

    server.load_engine(str(checkpoint_dir))
    port = free_port()
    http = make_server("127.0.0.1", port, server.app, threaded=True)
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{port}"

    try:
        import webview
    except ImportError:
        webview = None

    if webview is None:
        webbrowser.open(url)
        try:
            thread.join()
        except KeyboardInterrupt:
            pass
    else:
        webview.create_window("Vortex", url, width=480, height=780, min_size=(360, 520), background_color="#0b0912")
        icon = server.ROOT / "assets" / "icon.png"
        webview.start(icon=str(icon) if icon.exists() else None)

    http.shutdown()


if __name__ == "__main__":
    main()
