import json
import re

USER = "<|user|>"
BOT = "<|vortex|>"
END = "<|end|>"
UNK = "<|unk|>"
SPECIAL_TOKENS = [END, USER, BOT, UNK]

_SPLIT = re.compile("(" + "|".join(re.escape(t) for t in SPECIAL_TOKENS) + ")")


class CharTokenizer:
    def __init__(self, chars):
        self.itos = list(SPECIAL_TOKENS) + sorted(set(chars))
        self.stoi = {s: i for i, s in enumerate(self.itos)}

    @property
    def vocab_size(self):
        return len(self.itos)

    @property
    def end_id(self):
        return self.stoi[END]

    @property
    def user_id(self):
        return self.stoi[USER]

    @property
    def bot_id(self):
        return self.stoi[BOT]

    @classmethod
    def from_text(cls, text):
        plain = _SPLIT.sub("", text)
        return cls(plain)

    def encode(self, text):
        ids = []
        unk = self.stoi[UNK]
        for part in _SPLIT.split(text):
            if not part:
                continue
            if part in SPECIAL_TOKENS:
                ids.append(self.stoi[part])
            else:
                ids.extend(self.stoi.get(ch, unk) for ch in part)
        return ids

    def decode(self, ids, skip_special=True):
        out = []
        for i in ids:
            token = self.itos[i]
            if skip_special and token in SPECIAL_TOKENS:
                continue
            out.append(token)
        return "".join(out)

    def save(self, path):
        chars = [c for c in self.itos if c not in SPECIAL_TOKENS]
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"chars": chars}, f, ensure_ascii=False)

    @classmethod
    def load(cls, path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(data["chars"])
