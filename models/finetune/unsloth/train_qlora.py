"""QLoRA fine-tune of the Vortex base model with Unsloth, exported to GGUF.

Usage:
    python train_qlora.py --data ../data/vortex_identity.sample.jsonl --output ./out/vortex-v0.3
"""

from __future__ import annotations

import argparse

from datasets import load_dataset
from trl import SFTConfig, SFTTrainer
from unsloth import FastLanguageModel
from unsloth.chat_templates import get_chat_template


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", default="unsloth/Qwen2.5-7B-Instruct-bnb-4bit")
    p.add_argument("--data", required=True, help="JSONL file with OpenAI-style 'messages'")
    p.add_argument("--output", default="./out/vortex-v0.3")
    p.add_argument("--max-seq-len", type=int, default=4096)
    p.add_argument("--epochs", type=float, default=2.0)
    p.add_argument("--lr", type=float, default=2e-4)
    p.add_argument("--rank", type=int, default=16)
    p.add_argument("--batch-size", type=int, default=2)
    p.add_argument("--grad-accum", type=int, default=8)
    p.add_argument("--quant", default="q4_k_m", help="GGUF quantization method")
    p.add_argument("--no-gguf", action="store_true", help="Skip GGUF export")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.base,
        max_seq_length=args.max_seq_len,
        load_in_4bit=True,
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=args.rank,
        lora_alpha=args.rank * 2,
        lora_dropout=0.0,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )
    tokenizer = get_chat_template(tokenizer, chat_template="qwen-2.5")

    dataset = load_dataset("json", data_files=args.data, split="train")

    def to_text(batch: dict) -> dict:
        texts = [
            tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=False)
            for msgs in batch["messages"]
        ]
        return {"text": texts}

    dataset = dataset.map(to_text, batched=True, remove_columns=dataset.column_names)

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        args=SFTConfig(
            output_dir=args.output,
            dataset_text_field="text",
            max_seq_length=args.max_seq_len,
            per_device_train_batch_size=args.batch_size,
            gradient_accumulation_steps=args.grad_accum,
            num_train_epochs=args.epochs,
            learning_rate=args.lr,
            lr_scheduler_type="cosine",
            warmup_ratio=0.03,
            logging_steps=10,
            save_strategy="epoch",
            optim="adamw_8bit",
            seed=42,
            report_to="none",  # no telemetry
        ),
    )
    trainer.train()

    model.save_pretrained(f"{args.output}/lora")
    tokenizer.save_pretrained(f"{args.output}/lora")

    if not args.no_gguf:
        model.save_pretrained_gguf(f"{args.output}/gguf", tokenizer, quantization_method=args.quant)
        print(f"GGUF written to {args.output}/gguf; copy it into models/gguf/")


if __name__ == "__main__":
    main()
