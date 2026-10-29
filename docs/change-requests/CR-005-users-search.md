# CR-005: Search and filters on the Users list (four optional query parameters)

Follows the blueprint Change Request process (section 2). Status: **Treated as approved on 2026-10-29**: the owner approved the Phase 10B plan ("plan 10B great") that lists it.

## 1. What must change and why
The scale demo (Phase 10A) showed that with 1,009 accounts the Users screen reaches only the first 100 people: the website asks for one page of 100 (the API maximum) and cannot search or page. An administrator cannot find a person to edit or deactivate, and the member picker of the Groups screen has the same limit. The API already pages (`limit`, `offset`, `total`), but it cannot search or filter.

## 2. What it touches
The API contract, by adding only: four optional query parameters on one existing route. No table, no column, no migration, no new route.

## 3. Additive solution
`GET /users` (system_admin only, unchanged) accepts, in addition to `limit` and `offset`:
- `q` (text, at most 100 characters): a case-insensitive "contains" search in the e-mail and the full name. The person's own `%`, `_` and backslash are plain characters, not wildcards. A blank `q` is no search.
- `department_id` (integer, 1 or more): only people of that department.
- `is_active` (true or false): only active, or only deactivated, people.
- `role` (text, at most 64 characters): only people who have that role (a person with several roles is still listed once).

The filters combine (AND). The response keeps its shape: `items`, `total` (now the number of ALL people that match, not only the page), `limit`, `offset`. Order stays by e-mail, so paging is stable. Calls without the new parameters behave exactly as before.

Security: the route stays admin-only (checked on the server, from the database); the new parameters are validated (length limits, types, 422 on bad values) and are passed to the database as bound parameters, never inside SQL text.

## 4. Decision
Add the four parameters (implemented in Phase 10B) and use them in the Users screen and in the member picker of the Groups screen.

## 5. Consequences
- The contract grows by four optional parameters; no existing client is affected.
- The search is a plain `LIKE` with `lower()`: fine for thousands of people. For very many people (hundreds of thousands) a trigram index would be needed (backlog 59).
