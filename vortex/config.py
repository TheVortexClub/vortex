from dataclasses import dataclass, asdict


@dataclass
class ModelConfig:
    vocab_size: int = 0
    block_size: int = 256
    n_layer: int = 4
    n_head: int = 4
    n_embd: int = 192
    dropout: float = 0.1

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


@dataclass
class TrainConfig:
    data_dir: str = "data"
    out_dir: str = "checkpoints"
    batch_size: int = 32
    max_steps: int = 2000
    learning_rate: float = 1e-3
    min_learning_rate: float = 1e-4
    warmup_steps: int = 100
    weight_decay: float = 0.1
    grad_clip: float = 1.0
    eval_interval: int = 250
    eval_steps: int = 5
    val_split: float = 0.1
    augment_copies: int = 4
    seed: int = 1337
