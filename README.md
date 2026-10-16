<p align="center"><img src="assets/icon.png" width="128" alt="Vortex"></p>

# Vortex

A personal AI built from scratch in Python. Vortex is a small GPT-style transformer trained character by character on your own conversations, served through a local web chat. No external APIs, runs fully offline.

## Features

- Decoder-only transformer (GPT architecture) written in PyTorch
- Character-level tokenizer with special chat tokens
- Loss computed only on Vortex's replies, so it learns to answer instead of imitating you
- Data augmentation for user messages (case, accents, punctuation)
- Streaming web chat UI with Flask
- Terminal chat
- Desktop app with a native window (pywebview)
- Windows builds through GitHub Actions
- Runs on CPU, CUDA or Apple Silicon (MPS)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Train

```bash
python train.py
```

Useful options:

```bash
python train.py --max-steps 5000 --learning-rate 1e-3
python train.py --n-layer 6 --n-embd 256 --n-head 8
python train.py --resume --max-steps 2000
```

The model and tokenizer are saved to `checkpoints/`.

## Chat

Web:

```bash
python server.py
```

Then open http://127.0.0.1:5000

Terminal:

```bash
python chat.py
```

Desktop app:

```bash
pip install pywebview
python app.py
```

Without pywebview, the app opens in your default browser.

## Windows build

Every push to `main` runs `.github/workflows/build.yml`, which trains the model, packages Vortex with PyInstaller and uploads `Vortex-windows-x64` as an artifact. Pushing a tag like `v1.0.0` also publishes the zip as a GitHub release. You can run it manually from the Actions tab and choose the number of training steps.

To build locally on Windows:

```bash
pip install pyinstaller pywebview
python train.py
pyinstaller app.py --name Vortex --windowed --icon assets/icon.ico --add-data "web;web" --add-data "assets;assets" --add-data "checkpoints;checkpoints" --collect-submodules webview
```

A `checkpoints` folder placed next to `Vortex.exe` overrides the bundled model, so you can retrain without rebuilding.

## Teaching Vortex

Add `.txt` files to `data/`. Every file in that folder is used for training.

```
> what the user says
< what Vortex answers
> follow-up from the user
< Vortex's follow-up answer
---
> a new conversation starts after ---
< answer
```

Then train again. The more varied conversations you add, the better Vortex gets. Write several phrasings of the same question to help it generalize.

## Project layout

```
vortex/
  config.py      model and training settings
  tokenizer.py   character tokenizer with chat tokens
  model.py       GPT transformer
  data.py        conversation parser and batching
  engine.py      inference wrapper
train.py         training script
app.py           desktop app launcher
server.py        web server
chat.py          terminal chat
web/             chat interface
assets/          app icons
.github/         Windows build workflow
data/            training conversations
checkpoints/     trained model
```

## License

MIT
