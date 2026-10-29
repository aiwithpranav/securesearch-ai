# Phase 10: Scale demo (after v1.0)

Goal: show, with numbers, that SecureSearch AI keeps working and stays leak-free on a large body of real documents and many people, not only on the 48 invented documents and 8 people of the evaluation.

| Layer | Content | Status |
|---|---|---|
| **10A** Scale demo | A separate copy of the system (own database, own file store, own ports), about 100,000 passages from real public documentation, 1,000 synthetic people, a loader, a leak and speed check, a kept record of the results | Built and run in full (90,956 passages, 1,000 people, 0 leaks); Merged (PR #36) |
| **10B** Users list at scale | Search, filters and paging on the Users list (API: four optional query parameters, CR-005), a person picker (type to search) for the Groups members and for the document access rules, replacing the list of "the first 100 people" | Built, waiting for owner review |

## Why a separate stack
The normal stack and its data (the demo of Phase 1 to 9) are never touched. The scale demo is started with its own project name (`docker compose -p securesearch-big ...`), so its volumes are separate, and everything can be removed with one command when the space is needed again.

## What is kept after the data is deleted
The scripts, the documents in `docs/`, `RESULTS.md` (numbers, method, commands to recreate) and the screenshots. The data itself (database, downloaded files) is not kept: it can be rebuilt with the scripts.

## Sources (all public, nothing is committed to Git)
| Source | What | Licence |
|---|---|---|
| Kubernetes documentation | Engineering and operations pages | CC BY 4.0 |
| Docker documentation | Containers and Compose | Apache 2.0 |
| GitLab handbook | A real company's policies and processes (HR, finance, legal, security, engineering) | CC BY-SA 4.0 |

## Out of scope
Cloud deployment, a GPU reranker, replicas and single sign-on (see `docs/scale-and-limits.md` for the roadmap). The scale demo runs on one laptop and says so.
