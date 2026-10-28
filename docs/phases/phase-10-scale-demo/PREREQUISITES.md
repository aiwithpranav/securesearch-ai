# Phase 10 Prerequisites

- Docker Desktop running; Git and Git Bash.
- About 15 GB free on the drive where Docker keeps its data (on the owner's laptop that is C:). Estimate for 100,000 passages: database about 1 GB, downloaded Markdown a few hundred MB, build cache and models already exist. The first time Docker may need more for the indexing work.
- 16 GB of memory or more is comfortable: the worker runs three processes, each loads two models (about 1.2 GB each). Close other heavy applications and keep the charger connected: indexing 100,000 passages on a laptop CPU takes hours.
- Internet for the download (shallow clones from GitHub and GitLab).
- The normal `.env` (the big stack reuses the same settings and secrets; it has its own database).
- No OpenAI key is needed for the scale check (it measures search and permissions).
