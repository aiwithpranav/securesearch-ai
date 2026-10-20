# ADR 024: Pinned versions for Phase 3 (documents and ingestion)

## Status
Accepted (2026-10-20). Follows the blueprint versions policy: exact pins, versions at least two weeks old unless there was no choice, licences checked.

## Context
Phase 3 adds object storage, a background worker, file parsing and local embeddings. Every new tool must be pinned so builds are repeatable.

## Decision
| Item | Pin | Checked on 2026-10-19/20 |
|---|---|---|
| Object storage image | `chrislusf/seaweedfs:4.48` | Apache-2.0, released 2026-09-28 |
| Embedding model | `BAAI/bge-small-en-v1.5` at revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a` | **MIT licence**, `hidden_size` 384, last model change 2024-02-22 |
| `torch` | `2.14.1` (CPU-only wheel, `+cpu`) | Installed from `download.pytorch.org/whl/cpu` in the Dockerfile |
| `transformers` | `5.20.2` | Chosen by pip when resolving `sentence-transformers` |
| `huggingface_hub` | `1.33.0` | Used at build time to download the model |
| `sentence-transformers` | `6.1.0` | Released 2026-09-18 |
| `celery` | `5.6.3` (with `kombu 5.6.2`) | Dry-run install showed **no conflict** with our pinned `redis 8.1.0` |
| `boto3` | `1.43.108` | Released 2026-10-02 (newer 1.43.114 is under two weeks old) |
| `pypdf` | `6.19.0` | Released 2026-09-16 (6.21.1 is under two weeks old); used from 3B |
| `python-docx` | `1.2.0` | Used from 3B |
| `python-multipart` | `0.0.32` | FastAPI file uploads, used from 3B |

## Consequences
- The backend image is about **2.7 GB** (CPU PyTorch plus the model). The worker uses the same image (blueprint 8.6), so the API image carries the model too.
- The embedding model is **baked into the image at build time** (about 130 MB). Containers run with `HF_HUB_OFFLINE=1`, and the worker sits on the private network without internet. No document text can leave the machine.
- Changing the model later means a new vector column (blueprint 10.2), not editing this one.
- Torch is pinned in `requirements.txt` but installed first from the CPU index; both places must change together.
