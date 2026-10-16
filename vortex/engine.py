from pathlib import Path

import torch

from .config import ModelConfig
from .data import format_prompt
from .model import VortexGPT
from .tokenizer import CharTokenizer, BOT


class Vortex:
    def __init__(self, checkpoint_dir="checkpoints", device=None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        checkpoint_dir = Path(checkpoint_dir)
        self.tokenizer = CharTokenizer.load(checkpoint_dir / "tokenizer.json")
        state = torch.load(checkpoint_dir / "vortex.pt", map_location=self.device)
        self.config = ModelConfig.from_dict(state["config"])
        self.model = VortexGPT(self.config).to(self.device)
        self.model.load_state_dict(state["model"])
        self.model.eval()

    def stream(self, history, max_new_tokens=300, temperature=0.7, top_k=40, top_p=0.9):
        budget = self.config.block_size - 1
        turns = list(history)
        while True:
            ids = self.tokenizer.encode(format_prompt(turns) + BOT)
            if len(ids) <= budget or len(turns) <= 1:
                break
            turns = turns[1:]
        ids = ids[-budget:]
        idx = torch.tensor([ids], dtype=torch.long, device=self.device)
        for token_id in self.model.generate(
            idx,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
            stop_id=self.tokenizer.end_id,
        ):
            if token_id in (self.tokenizer.user_id, self.tokenizer.bot_id):
                break
            yield self.tokenizer.decode([token_id])

    def reply(self, history, **kwargs):
        return "".join(self.stream(history, **kwargs)).strip()
