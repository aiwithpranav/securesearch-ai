# Phase 10: Scale demo results

This record stays in the repository after the big stack and the downloaded files are deleted.

> **Status: the full run is done** (2026-10-29, code at commit `3e34408`, on the owner's laptop CPU). Everything below was measured. Where a result is weak, it says so.

## What is tested
- 5,850 real public documents (Kubernetes, Docker, the GitLab handbook), **90,956 passages**, 1,000 synthetic people, 6,479 access rules (team by role, executives for restricted pages, clearance gate).
- Search time per mode (keyword, vector, hybrid, hybrid with the reranker) on natural questions made from page titles.
- A leak check: people who must not read a document search for it (the tail of its marked passage, and the bare marker); an independent oracle checks every hit of every query. The expected result is **0 violations**.

## Results of the full run
| Measure | Result |
|---|---|
| Documents / passages | 5,850 / 90,956 (about 91 percent of the 100,000 aimed at: the public Markdown holds about 80 MB of text) |
| People / access rules | 1,000 / 6,479 |
| Loading (upload and rules) | 5 min 42 s |
| Indexing (parse, chunk, embed), 3 worker processes on a laptop CPU | about 1 h 50 min (about 14 passages per second) |
| Database size | 507 MB (the passages table with its indexes 485 MB, of which indexes 210 MB): about 5.3 KB per passage |
| Search, keyword: median / P95 | 79 ms / 406 ms |
| Search, vector: median / P95 | 76 ms / 214 ms |
| Search, hybrid: median / P95 | 243 ms / 485 ms |
| Search, hybrid + reranker (the default): median / P95 | **4.6 s / 5.4 s** |
| Queries checked against the oracle | 1,040 (60 questions in each of the 4 modes, 300 forbidden documents searched twice, 100 allowed documents searched twice) |
| **Leaks / violations** | **0** |
| Comparison with the normal demo | 120 passages, 9 people, 80 rules; evaluation P95 search 2.0 s |

## What the run showed (honest findings)
1. **No leak.** 1,040 queries, every hit of every query compared with the independent oracle: 0 violations. Two earlier checks (a first full run with another query form: 640 queries, and the 30-file trial) also gave 0.
2. **The leak search is strong, not perfect.** Searching with the tail of a marked passage, people who MAY read the document found it in the top results 87 times out of 100. That is the strength of the test: a real leak of such a document would be surfaced about 87 percent of the time per search, and 300 forbidden searches were made. It is not proof of absence in the way the 62-case evaluation's scanner is, but it is strong evidence at this size.
3. **Exact-identifier search is weak at this size.** A bare marker (a unique code) was found by people who may read it only 25 times out of 100 (14 of 100 in the first run, with a longer sentence around the code), against 15 of 15 on 60 passages. The keyword search ranks with `ts_rank_cd`, which does not weigh how rare a word is (it is not BM25), so a rare code among thousands of passages is not ranked first. This matters for users who search for ticket numbers or error codes. Backlog 55.
4. **The default search is slower than the 5 s target at the 95th percentile on this laptop** (P95 5.4 s, median 4.6 s; target in the blueprint: P95 under 5 s). The reranker is the cost: real documentation passages are longer than the invented ones of the evaluation. Measured in isolation, reranking 20 real passages took 2.55 s, the same 20 cut to 20 words took 0.73 s. The rest of the 4.6 s (retrieval, loading, the CPU shared with other work) was not profiled further. Levers: fewer candidates, a GPU, a cap on passage length. Backlog 56.
5. **Without the reranker**, hybrid search stays under half a second at P95 even at 91,000 passages, so the database side (permission filter, full-text, HNSW vector index) is not the bottleneck at this size.
6. **Space is not a problem**: about 5.3 KB per passage; 1 million passages would need roughly 5 GB.

7. **Written answers on real technical documentation: explanations work, "how to" answers with commands are often refused.** A live check with the real model (2026-10-29, through the browser and the API, as people with and without the right role):

| Person | Question | Result |
|---|---|---|
| Engineer (`swara@demo`) | What is a Kubernetes Deployment? / What is a Pod in Kubernetes? / Why should containers run as a non-root user? | Answered with 2 to 4 cited sources each |
| HR manager (`dhanashree@demo`) | What is the parental leave policy? / How does GitLab handle vacation and time off? | Answered with cited sources |
| Engineer | What is the parental leave policy? (HR documents) | Refused (uniform refusal) |
| HR manager, finance analyst | What is a Kubernetes Deployment? (engineering documents) | Refused (uniform refusal) |
| Finance analyst | What is the parental leave policy? | Refused (uniform refusal) |
| Engineer | How do I roll back a deployment in Kubernetes? | **Refused**, although search ranked the right pages first (best score 0.997). The log shows the reason `UNSAFE_OUTPUT` after two model calls. |

   The last row is a real limitation of the answer validator ([ADR 030](../../adr/030-grounded-answers.md)): it blocks replies that contain links, HTML-like text or code. Technical answers very often contain command lines with placeholders such as `<name>` or code blocks. The blocked text is never logged by design, so the exact trigger was not seen; this is the most likely cause. Permissions and leak protection were not involved. Backlog 57.

8. **The Users screen shows only the first 100 people.** Found by looking at the screen with 1,009 accounts. The website asks for one page of 100 (`/users?limit=100`, the API maximum) and has no next-page control, so the other 909 people cannot be reached from the screen (the API itself pages correctly: `total` is 1,009 and `offset` works; the Documents screen and the Overview were fine at 5,850 documents). It was invisible with 9 demo people. Backlog 58. **Fixed in Phase 10B** (search, filters and paging; see its walkthrough).
9. **Screens that are empty in the scale stack are expected:** Evaluation (the 62-case evaluation runs in the normal demo stack; the scale check is `big_check`), Groups (access in this stack uses roles) and Sources (nothing is synced from GitHub).

Screenshots: not taken in this run (a record of the numbers is kept instead).

## Trial run (measured, small; before the full run)
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
