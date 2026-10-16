import random
import unicodedata
from pathlib import Path

import torch

from .tokenizer import USER, BOT, END


def parse_conversations(text):
    conversations = []
    for chunk in text.split("\n---"):
        turns = []
        role = None
        buffer = []
        for raw in chunk.strip().splitlines():
            line = raw.rstrip()
            if line.startswith("#") or line.strip() == "---":
                continue
            if line.startswith("> "):
                if role is not None and buffer:
                    turns.append((role, "\n".join(buffer).strip()))
                role, buffer = "user", [line[2:]]
            elif line.startswith("< "):
                if role is not None and buffer:
                    turns.append((role, "\n".join(buffer).strip()))
                role, buffer = "bot", [line[2:]]
            elif line.strip() and role is not None:
                buffer.append(line)
        if role is not None and buffer:
            turns.append((role, "\n".join(buffer).strip()))
        if any(r == "bot" for r, _ in turns):
            conversations.append(turns)
    return conversations


def load_conversations(data_dir):
    conversations = []
    for path in sorted(Path(data_dir).glob("*.txt")):
        conversations.extend(parse_conversations(path.read_text(encoding="utf-8")))
    return conversations


def strip_accents(text):
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )


def augment_user(text, rng):
    variants = [
        text,
        text.lower(),
        text.lower().rstrip("?!.,"),
        strip_accents(text.lower()),
        text[:1].upper() + text[1:],
        strip_accents(text.lower()).rstrip("?!.,"),
    ]
    return rng.choice(variants)


def format_prompt(history):
    parts = []
    for role, content in history:
        if role == "user":
            parts.append(USER + content)
        else:
            parts.append(BOT + content + END)
    return "".join(parts)


def encode_conversation(turns, tokenizer, rng=None):
    ids = []
    mask = []
    for role, content in turns:
        if role == "user":
            if rng is not None:
                content = augment_user(content, rng)
            piece = tokenizer.encode(USER + content)
            ids.extend(piece)
            mask.extend([0] * len(piece))
        else:
            head = tokenizer.encode(BOT)
            body = tokenizer.encode(content + END)
            ids.extend(head)
            mask.extend([0] * len(head))
            ids.extend(body)
            mask.extend([1] * len(body))
    return ids, mask


class ConversationDataset:
    def __init__(self, conversations, tokenizer, block_size, augment_copies=0, seed=0):
        rng = random.Random(seed)
        self.block_size = block_size
        self.samples = []
        for turns in conversations:
            self.samples.append(encode_conversation(turns, tokenizer))
            for _ in range(augment_copies):
                self.samples.append(encode_conversation(turns, tokenizer, rng))

    def __len__(self):
        return len(self.samples)

    def batch(self, batch_size, rng, device):
        x = torch.full((batch_size, self.block_size), 0, dtype=torch.long)
        y = torch.full((batch_size, self.block_size), -1, dtype=torch.long)
        for row in range(batch_size):
            ids, mask = rng.choice(self.samples)
            span = self.block_size + 1
            if len(ids) > span:
                start = rng.randint(0, len(ids) - span)
                ids, mask = ids[start:start + span], mask[start:start + span]
            n = len(ids) - 1
            x[row, :n] = torch.tensor(ids[:-1])
            targets = torch.tensor(ids[1:])
            keep = torch.tensor(mask[1:], dtype=torch.bool)
            targets[~keep] = -1
            y[row, :n] = targets
        return x.to(device), y.to(device)
