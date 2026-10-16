# Fine-tuning Vortex (LoRA / QLoRA)

Two options for training a LoRA adapter on top of the base model, then exporting it to GGUF so
Ollama or llama.cpp can serve it as a new Vortex version.

| Path | When to use |
|---|---|
| `unsloth/` | One consumer GPU (8–24 GB VRAM). Fastest QLoRA, exports GGUF directly. |
| `axolotl/` | Multiple GPUs or more control over the training recipe. |

## Dataset format

JSONL, one conversation per line, OpenAI chat format (see `data/vortex_identity.sample.jsonl`):

```json
{"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
```

Keep the system prompt the same as `models/prompts/vortex-system.md` so training matches serving.

## Unsloth (single GPU)

```bash
cd models/finetune/unsloth
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python train_qlora.py --data ../data/vortex_identity.sample.jsonl --output ./out/vortex-v0.3
```

The script saves the LoRA adapter and a `Q4_K_M` GGUF. Copy the GGUF into `models/gguf/`.

## Axolotl

```bash
pip install axolotl[flash-attn,deepspeed]
axolotl train axolotl/vortex-qlora.yaml
axolotl merge-lora axolotl/vortex-qlora.yaml
# convert to GGUF with llama.cpp: convert_hf_to_gguf.py + llama-quantize ... Q4_K_M
```

## Serving the result as a new version

1. Ollama: point `FROM` in `models/Modelfile` at the GGUF, then run
   `ollama create vortex:0.3 -f models/Modelfile`.
   llama.cpp: put the GGUF in `models/gguf/` and start the `llamacpp` compose profile.
2. Add a `vortex-v0.3` entry to `models/registry.yaml` (there is a commented example).
3. Restart the API. The new model appears in `GET /v1/models`.
