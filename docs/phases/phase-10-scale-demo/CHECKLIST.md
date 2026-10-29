# Phase 10 Checklist

## 10A Scale demo
- [x] `docker-compose.big.yml`: second stack with its own ports (18000, 18025), the document folder mounted read-only, three worker processes
- [x] `scripts/big/download.sh`: shallow, sparse download of the three public sources (Markdown only) outside the repository
- [x] `app/scale/corpus.py`: placement by path (department, type, sensitivity), access rules, front matter and shortcode cleaning, canary markers
- [x] `app/scale/people.py`: deterministic synthetic people (departments, roles, clearance, countries)
- [x] `app/scale/oracle.py`: independent fast oracle, compared with the SQL resolver in random worlds
- [x] `app/scripts/big_load.py` and `big_check.py` (status, latency per mode, leak check, report)
- [x] 27 tests in `tests/test_scale.py`; mypy and ruff clean
- [x] Trial run on 30 files and 200 people in a throw-away stack: all READY, 0 violations; a deliberate mistake in the resolver (clearance ignored) was caught (33 violations)
- [x] Docs: this folder, ADR 039, `docs/error-handling.md`, `docs/scale-and-limits.md`
- [x] Owner approval, PR #36 merged
- [ ] Tag `v1.1` (after 10B, with one release note for both layers)
- [x] Full run (2026-10-29): 5,850 real documents, 90,956 passages, 1,000 people, 6,479 rules; 1,040 queries checked, **0 violations**; `RESULTS.md` filled with the real numbers (and the weak spots: exact-identifier search, P95 5.4 s)
- [ ] Optional later: delete the big stack (`down -v`) and the downloaded folder when space is needed; the record stays

## 10B Users list at scale
- [x] CR-005: `GET /users` gets `q`, `department_id`, `is_active` and `role` (all optional, additive, admin only); `total` counts all matches
- [x] 11 backend tests (`tests/test_users_search.py`); 9 mutation checks caught, 2 equivalent (the e-mail is always lower case by a database rule; a blank search is trimmed to nothing)
- [x] Users screen: search, department, role and status filters, Previous / Next with "x to y of N", stale answers ignored, "No one matches" state
- [x] `UserPicker` (type to search, server side) for the Groups members and for the document access rules ("Who" for a person, "Who can read this?" preview)
- [x] 8 frontend tests; lint ceiling unchanged (21), types and build clean
- [x] Real browser check on the scale stack (1,009 people): 15 of 15 checks (total, 50 per page, Next to the last page, search beyond the first 100, no match, role and status filters, Clear, the access rule picker, no sideways scrolling at 360 px)
- [ ] Owner approval, PR merged, tag `v1.1`
