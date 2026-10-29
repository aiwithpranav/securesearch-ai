# ADR 039: The scale demo (Phase 10A)

## Status
Accepted (2026-10-25). The owner approved the Phase 10 plan ("plan ok") with its five decisions. The owner can reverse any item.

## Context
Phases 1 to 9 are frozen and released as v1.0. The evaluation proves zero leaks on 62 cases over 48 invented documents and 8 people. Open question from a reviewer: does it still work with many documents and many people, and on real documents? Nothing in the repository measured that. The data for such a test is large, should not be committed and should be easy to delete when disk space is needed.

## Decision
- **A new phase, a new version (v1.1).** Phases 1 to 9 are not edited.
- **A separate stack.** `docker-compose.big.yml` is an override used with its own project name. It changes only the published ports (18000 and 18025), mounts the document folder read-only and runs three worker processes. Volumes and networks are separate by project name, so `down -v` removes the whole demo and the normal stack is untouched.
- **Data stays outside Git.** `scripts/big/download.sh` fetches only the Markdown pages of three public sources (Kubernetes documentation, Docker documentation, the GitLab handbook) by shallow, sparse clone into `BIG_DATA_DIR`. Licences and attribution are recorded in `RESULTS.md`.
- **The real pipeline is measured.** Documents go through the normal upload service and the normal worker. The only added step is cleaning: site-generator front matter, shortcodes and comments are removed because they are build instructions, not knowledge.
- **People and rules.** Synthetic people with a department, roles, clearance and country, all sharing the demo password (hashed once). Documents are placed by path (department, type, sensitivity). Team documents are opened by role, not by department, so the system administrator, who sits in Engineering, still does not read them ("admin is not reader"). Executives may also read restricted documents. The clearance gate applies as everywhere.
- **Leak check with an independent oracle.** Restricted documents (and about one in twenty others) carry a canary marker. People who must not read a document search for its marker; every hit of every query, including the latency queries, is compared with a plain-Python oracle that indexes rules by document (`app/scale/oracle.py`, compared with the SQL resolver in random worlds in `tests/test_scale.py`). One violation fails the run.
- **Honest reporting.** `RESULTS.md` is the kept record. It says "not done yet" until the full run is done, and it keeps the method and the commands to recreate the data after the data is deleted.

## Consequences
- The full run needs hours of CPU time, about 15 GB of free disk and the owner's permission for the download.
- Natural-question latency uses page titles as questions: it measures speed, not answer quality.
- The scale demo is one machine. Cloud scale, a GPU reranker, replicas and cost are written down as a roadmap in `docs/scale-and-limits.md`, not measured.
- Docker image rebuilds were not needed for the scripts in the trial (they were copied into a throw-away container); the next normal image build includes them.
