import argparse
import math
import random
import time
from dataclasses import fields
from pathlib import Path

import torch

from vortex.config import ModelConfig, TrainConfig
from vortex.data import ConversationDataset, load_conversations
from vortex.model import VortexGPT
from vortex.tokenizer import CharTokenizer


def parse_args():
    parser = argparse.ArgumentParser(description="Train Vortex from scratch")
    for cfg in (TrainConfig, ModelConfig):
        for f in fields(cfg):
            if f.name == "vocab_size":
                continue
            parser.add_argument(f"--{f.name.replace('_', '-')}", type=type(f.default), default=f.default)
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


def build_configs(args):
    values = vars(args)
    train_cfg = TrainConfig(**{f.name: values[f.name] for f in fields(TrainConfig)})
    model_cfg = ModelConfig(**{f.name: values[f.name] for f in fields(ModelConfig) if f.name != "vocab_size"})
    return train_cfg, model_cfg


def learning_rate(step, cfg):
    if step < cfg.warmup_steps:
        return cfg.learning_rate * (step + 1) / cfg.warmup_steps
    progress = (step - cfg.warmup_steps) / max(1, cfg.max_steps - cfg.warmup_steps)
    cosine = 0.5 * (1.0 + math.cos(math.pi * min(1.0, progress)))
    return cfg.min_learning_rate + cosine * (cfg.learning_rate - cfg.min_learning_rate)


@torch.no_grad()
def evaluate(model, datasets, cfg, rng, device):
    model.eval()
    result = {}
    for name, ds in datasets.items():
        losses = []
        for _ in range(cfg.eval_steps):
            x, y = ds.batch(cfg.batch_size, rng, device)
            _, loss = model(x, y)
            losses.append(loss.item())
        result[name] = sum(losses) / len(losses)
    model.train()
    return result


def save(model, model_cfg, tokenizer, out_dir, step, best_val):
    out_dir.mkdir(parents=True, exist_ok=True)
    tokenizer.save(out_dir / "tokenizer.json")
    torch.save(
        {"model": model.state_dict(), "config": model_cfg.to_dict(), "step": step, "best_val": best_val},
        out_dir / "vortex.pt",
    )


def main():
    args = parse_args()
    train_cfg, model_cfg = build_configs(args)
    torch.manual_seed(train_cfg.seed)
    rng = random.Random(train_cfg.seed)
    device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
    out_dir = Path(train_cfg.out_dir)

    conversations = load_conversations(train_cfg.data_dir)
    if not conversations:
        raise SystemExit(f"No conversations found in {train_cfg.data_dir}/*.txt")

    corpus = "\n".join(content for turns in conversations for _, content in turns)
    if args.resume and (out_dir / "tokenizer.json").exists():
        tokenizer = CharTokenizer.load(out_dir / "tokenizer.json")
    else:
        tokenizer = CharTokenizer.from_text(corpus)
    model_cfg.vocab_size = tokenizer.vocab_size

    rng.shuffle(conversations)
    n_val = max(1, int(len(conversations) * train_cfg.val_split))
    val_convs = conversations[:n_val]
    train_convs = conversations
    train_ds = ConversationDataset(train_convs, tokenizer, model_cfg.block_size, train_cfg.augment_copies, train_cfg.seed)
    val_ds = ConversationDataset(val_convs, tokenizer, model_cfg.block_size)

    model = VortexGPT(model_cfg).to(device)
    start_step = 0
    best_val = float("inf")
    if args.resume and (out_dir / "vortex.pt").exists():
        state = torch.load(out_dir / "vortex.pt", map_location=device)
        model.load_state_dict(state["model"])
        start_step = state.get("step", 0)
        best_val = state.get("best_val", best_val)

    decay = [p for n, p in model.named_parameters() if p.dim() >= 2]
    no_decay = [p for n, p in model.named_parameters() if p.dim() < 2]
    optimizer = torch.optim.AdamW(
        [{"params": decay, "weight_decay": train_cfg.weight_decay}, {"params": no_decay, "weight_decay": 0.0}],
        lr=train_cfg.learning_rate,
        betas=(0.9, 0.95),
    )

    print(f"device={device} params={model.num_params() / 1e6:.2f}M vocab={tokenizer.vocab_size} "
          f"conversations={len(conversations)} train_samples={len(train_ds)}")

    model.train()
    started = time.time()
    end_step = start_step + train_cfg.max_steps if args.resume else train_cfg.max_steps
    for step in range(start_step, end_step):
        lr = learning_rate(step - start_step, train_cfg)
        for group in optimizer.param_groups:
            group["lr"] = lr
        x, y = train_ds.batch(train_cfg.batch_size, rng, device)
        _, loss = model(x, y)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), train_cfg.grad_clip)
        optimizer.step()

        if step % train_cfg.eval_interval == 0 or step == end_step - 1:
            losses = evaluate(model, {"train": train_ds, "val": val_ds}, train_cfg, rng, device)
            elapsed = time.time() - started
            print(f"step {step:5d} | train {losses['train']:.4f} | val {losses['val']:.4f} | lr {lr:.2e} | {elapsed:.0f}s")
            best_val = min(best_val, losses["val"])
            save(model, model_cfg, tokenizer, out_dir, step + 1, best_val)

    print(f"saved to {out_dir}/vortex.pt")


if __name__ == "__main__":
    main()
