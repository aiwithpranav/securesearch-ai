# Phase 10: Scale demo results

This record stays in the repository after the big stack and the downloaded files are deleted.

> **Status: the full run has not been done yet.** The numbers below are filled in after it. Until then, the only measured result is the small trial (see "Trial run"). Nothing in this file claims a number that was not measured.

## What is tested
- About 100,000 passages from real public documentation (Kubernetes, Docker, the GitLab handbook), 1,000 synthetic people, access rules by team, clearance and executives.
- Search time per mode (keyword, vector, hybrid, hybrid with the reranker) on natural questions.
- A leak check: people who must not read a document search for that document's canary marker; an independent oracle checks every hit of every query. The expected result is **0 violations**.

## Results of the full run
| Measure | Result |
|---|---|
| Date and commit | (to fill) |
| Documents / passages | (to fill) |
| People / access rules | (to fill) |
| Indexing time (laptop CPU, 3 worker processes) | (to fill) |
| Database size | (to fill) |
| Search, keyword: median / P95 | (to fill) |
| Search, vector: median / P95 | (to fill) |
| Search, hybrid: median / P95 | (to fill) |
| Search, hybrid + reranker (default): median / P95 | (to fill) |
| Queries checked against the oracle | (to fill) |
| **Leaks / violations** | (to fill) |
| Comparison with the normal demo (120 passages) | (to fill) |

Screenshots: (to add under `docs/images/scale/`).

## Trial run (measured, small)
30 files, 200 people, 60 passages, 41 rules, in a throw-away stack on the same code:

| Measure | Result |
|---|---|
| Queries checked against the oracle | 93 |
| Forbidden-marker searches (must find nothing) | 30 |
| Allowed-marker searches found in the top results | 15 of 15 |
| **Violations** | **0** |
| Search hybrid + reranker, median / P95 (60 passages, laptop CPU) | about 0.6 s / about 2.5 s |

Proof that the check can fail: with a deliberate mistake in the access resolver (the clearance check always true) the same check reported 33 violations.

## How to recreate this run
Needs Docker, Git Bash, about 15 GB free and a few hours of CPU time. Use Git Bash from the repository root.
```bash
export BIG_DATA_DIR=C:/Users/<you>/ss-big          # where the documents go (short path, outside the repository)
bash scripts/big/download.sh                         # Kubernetes, Docker, GitLab handbook (Markdown only)
C="docker compose -p securesearch-big -f docker-compose.yml -f docker-compose.big.yml"
$C up -d
$C exec backend alembic upgrade head
$C exec backend python -m app.scripts.seed_users
$C exec backend python -m app.scripts.big_load --users 1000
$C exec backend python -m app.scripts.big_check --status   # repeat until every document is READY
$C exec backend python -m app.scripts.big_check            # the report; exit code 1 means a leak
```
To look at it in the browser: stop the normal website, then from `frontend/` run `NEXT_PUBLIC_API_URL=http://localhost:18000 npm run dev`; sign in as `swara@demo` (or `big0001@demo`) with the demo password.

To delete everything of the scale demo (the normal stack is not affected):
```bash
$C down -v
rm -rf "$BIG_DATA_DIR"
```
Do not run `docker volume prune` or `docker system prune --volumes` while the data is wanted: they would delete it too.

## Attribution of the documents
- Kubernetes documentation, https://github.com/kubernetes/website, CC BY 4.0 (The Kubernetes Authors, The Linux Foundation).
- Docker documentation, https://github.com/docker/docs, Apache License 2.0.
- GitLab handbook, https://gitlab.com/gitlab-com/content-sites/handbook, CC BY-SA 4.0 (GitLab Inc.).
The documents are used only for this test, were changed only by the cleaning described in the walkthrough (front matter and shortcodes removed, a canary line added to some), and are not redistributed in this repository.
