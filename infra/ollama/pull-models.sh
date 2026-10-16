#!/bin/sh
# 1. Pulls the open-weight base and embedding models (VORTEX_PULL_MODELS, space-separated).
# 2. Builds the Vortex model (VORTEX_MODEL_NAME) from models/Modelfile on top of VORTEX_BASE_MODEL.
set -e

for model in $VORTEX_PULL_MODELS; do
  echo "[vortex] pulling $model ..."
  ollama pull "$model"
done

echo "[vortex] building $VORTEX_MODEL_NAME from $VORTEX_BASE_MODEL ..."
sed "s|^FROM .*|FROM $VORTEX_BASE_MODEL|" /init/Modelfile > /tmp/Modelfile
ollama create "$VORTEX_MODEL_NAME" -f /tmp/Modelfile

echo "[vortex] models ready"
