import argparse
import sys

from vortex.engine import Vortex


def main():
    parser = argparse.ArgumentParser(description="Chat with Vortex in the terminal")
    parser.add_argument("--checkpoint-dir", default="checkpoints")
    parser.add_argument("--temperature", type=float, default=0.7)
    args = parser.parse_args()

    vortex = Vortex(args.checkpoint_dir)
    history = []
    print("Vortex ready. Type 'exit' to quit.\n")
    while True:
        try:
            text = input("you > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not text:
            continue
        if text.lower() in ("exit", "quit"):
            break
        history.append(("user", text))
        sys.stdout.write("vortex > ")
        answer = ""
        for piece in vortex.stream(history, temperature=args.temperature):
            answer += piece
            sys.stdout.write(piece)
            sys.stdout.flush()
        sys.stdout.write("\n\n")
        history.append(("bot", answer.strip()))


if __name__ == "__main__":
    main()
