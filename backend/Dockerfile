FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    EMBEDDING_MODEL_PATH=/opt/models/bge-small-en-v1.5 \
    RERANKER_MODEL_PATH=/opt/models/bge-reranker-base \
    HF_HUB_OFFLINE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN adduser --disabled-password --gecos '' appuser

WORKDIR /app
RUN chown appuser:appuser /app

COPY requirements.txt requirements-dev.txt ./

# CPU-only PyTorch first. The default Linux wheel pulls about 2 GB of CUDA libraries we do not need.
RUN pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
RUN pip install -r requirements.txt -r requirements-dev.txt

# Bake the embedding model into the image at BUILD time (this is the only step that needs internet).
# At run time the containers are offline (HF_HUB_OFFLINE=1): no document text ever leaves the machine.
# The revision is pinned to an exact commit of BAAI/bge-small-en-v1.5 (MIT licence, 384 dimensions).
RUN HF_HUB_OFFLINE=0 python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='BAAI/bge-small-en-v1.5', revision='5c38ec7c405ec4b44b94cc5a9bb96e735b38267a', local_dir='/opt/models/bge-small-en-v1.5', allow_patterns=['*.json', '*.txt', 'model.safetensors', '1_Pooling/*'])"

# Same for the cross-encoder reranker (BAAI/bge-reranker-base, MIT licence), pinned to an exact commit.
RUN HF_HUB_OFFLINE=0 python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='BAAI/bge-reranker-base', revision='2cfc18c9415c912f9d8155881c133215df768a70', local_dir='/opt/models/bge-reranker-base', allow_patterns=['*.json', 'model.safetensors', 'sentencepiece.bpe.model'])"

USER appuser

COPY --chown=appuser:appuser . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
