# Scale, limits and what comes next

An honest page: what has been measured, what has not, where the system is expected to reach its limits, and what would be done about it.

## 1. What has been tested
| Scope | Result |
|---|---|
| 62 evaluation cases, 8 people, 48 invented documents | 0 leaks, Recall@5 1.00, P95 search 2.0 s ([evaluation report](evaluation-report.md)) |
| Scale demo (Phase 10), about 100,000 passages of real public documentation and 1,000 synthetic people on one laptop | See [RESULTS.md](phases/phase-10-scale-demo/RESULTS.md). Until its table is filled, nothing is claimed at that size. |

## 2. Why it is expected to scale reasonably (a design argument, not a measurement)
- Permissions are SQL inside PostgreSQL, so the database does the work and can be indexed and tuned.
- Vector search uses an HNSW index (approximate nearest neighbour), built for millions of vectors.
- Ingestion and sync run in background workers that can be multiplied; sync is incremental.
- Everything runs in containers and can be moved to servers.

## 3. Where it is expected to hit limits
| Limit | Why | What would be done (in order) |
|---|---|---|
| The allowed-documents query | Each search selects the readable documents first; with very many rules this grows | Look at the query plan and indexes; then precomputed ("materialised") access tables, with the "revoked means refused at once" scenarios kept in the test suite |
| The reranker | About 2 s per question on a laptop CPU, and it competes with other work | GPU, fewer candidates, batching |
| One machine | One point of failure; limited memory and CPU | Several API and worker replicas, a database replica, a load balancer |
| Database tuning | Connection count, HNSW settings | A connection pooler, parameter tuning, a read replica |
| Sync reads every file again | Wasteful for large sources | A content hint such as the Git blob id (backlog 40), parallel indexing, batched embeddings |
| Small evaluation | 62 cases, invented documents | A larger, real evaluation set, and a run with the real model |
| Sign-in | Email and password only | Single sign-on (OIDC or SAML) and automatic provisioning |

Security must not weaken while scaling: any optimisation of access (such as precomputed tables) is accepted only if the leak gate and the scenario tests still pass, above all "a revoked rule applies on the next question".

## 4. Cost (rough planning ranges, not quotes)
These are estimates for orientation, not measured and not provider quotes. Check the providers' price calculators before planning.
- **Laptop (what exists):** no cost except the model provider (a few tenths of a cent per answer at most; the live check of 8 questions cost about $0.0005).
- **Small pilot (about one cloud server):** in the order of a hundred to a few hundred US dollars per month.
- **Medium (several servers, a managed database, a GPU for the reranker):** in the order of a few hundred to a few thousand US dollars per month.
- **Large:** replicas, monitoring, single sign-on and a support team; mostly people cost.
Free options exist for learning (the laptop, or a free cloud tier with a small server), but not for a large corpus, a GPU or many users.

## 5. Why there are no agents (ReAct, tools)
The model has no tools on purpose. It only writes wording from passages that the access resolver already allowed; its reply is validated before anyone sees it ([ADR 030](adr/030-grounded-answers.md)). With tools, a successful prompt injection could become an action instead of a changed sentence. Agents are a reasonable next step only after a design in which every tool call is itself permission-checked and audited.

## 6. Retries and fallbacks
Listed in [error-handling.md](error-handling.md), section 7. Not built: a second model provider, a circuit breaker for the model provider, exponential backoff on API calls.

## 7. Roadmap summary
1. Run the scale demo and keep its record (Phase 10).
2. Load test further (more passages, concurrent users) and tune the allowed-documents query.
3. Real-model evaluation run; model fallback and circuit breaker.
4. Single sign-on, more connectors, deployment on servers.
