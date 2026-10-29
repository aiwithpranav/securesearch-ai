"""The Users list: paging, search and filters (Phase 10B).

The screen used to show only the first 100 people. The list now pages (limit and offset with the real total), searches
the e-mail and the name (contains, any case, the person's own % and _ are not wildcards) and filters by department,
status and role. Only the system administrator may call it, with or without these parameters."""
from tests.test_users_admin import _admin, _ids


def _list(api, token, **params):
    resp = api.request("GET", "/users", token=token, params=params)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _emails(body):
    return [u["email"] for u in body["items"]]


def test_search_finds_part_of_the_email_or_the_name_in_any_case(api, make_user):
    token = _admin(api, make_user)
    for e in ("meera@demo", "nina@demo", "vikram@demo"):
        make_user(e)
    assert _emails(_list(api, token, q="MEER")) == ["meera@demo"]  # part of the e-mail, upper case
    assert _emails(_list(api, token, q="Vikram")) == ["vikram@demo"]  # the name is the e-mail's first part, title-cased
    assert _list(api, token, q="demo")["total"] == 4  # the three plus the administrator
    assert _list(api, token, q="nobody-has-this")["total"] == 0


def test_search_also_looks_at_the_full_name_when_the_email_does_not_contain_it(api, make_user, pg):
    token = _admin(api, make_user)
    make_user("zz1@demo")
    make_user("zz2@demo")
    pg.execute("UPDATE users SET full_name='Priya Kulkarni' WHERE email='zz1@demo'")
    assert _emails(_list(api, token, q="kulkarni")) == ["zz1@demo"]  # only the name has it
    assert _emails(_list(api, token, q="PRIYA KUL")) == ["zz1@demo"]  # any case, across a space


def test_blank_search_is_no_search(api, make_user):
    token = _admin(api, make_user)
    make_user("meera@demo")
    assert _list(api, token, q="   ")["total"] == 2
    assert _list(api, token)["total"] == 2


def test_percent_underscore_and_backslash_are_plain_characters(api, make_user):
    token = _admin(api, make_user)
    make_user("a_b@demo")
    make_user("axb@demo")
    assert _emails(_list(api, token, q="a_b")) == ["a_b@demo"]  # an underscore is not 'any character'
    assert _list(api, token, q="%")["total"] == 0  # a percent sign is not 'everything'
    assert _list(api, token, q="\\")["total"] == 0  # a backslash does not break the pattern


def test_hostile_text_in_the_search_is_just_text(api, make_user):
    token = _admin(api, make_user)
    make_user("meera@demo")
    body = _list(api, token, q="'; drop table users; --")
    assert body["total"] == 0
    assert _list(api, token)["total"] == 2  # the table is still there


def test_paging_keeps_the_real_total_and_shows_every_person_exactly_once(api, make_user):
    token = _admin(api, make_user)
    for n in range(120):
        make_user(f"p{n:03d}@demo")
    seen: list[str] = []
    for offset in (0, 50, 100):
        body = _list(api, token, limit=50, offset=offset)
        assert body["total"] == 121 and body["limit"] == 50 and body["offset"] == offset
        seen += _emails(body)
    assert len(seen) == 121 and len(set(seen)) == 121  # nobody twice, nobody missing
    assert seen == sorted(seen)  # a stable order (by e-mail)
    body = _list(api, token, limit=50, offset=500)
    assert body["items"] == [] and body["total"] == 121  # past the end: nothing, and the total is still right


def test_the_total_counts_all_matches_not_only_the_page(api, make_user):
    token = _admin(api, make_user)
    for n in range(30):
        make_user(f"team{n:02d}@demo")
    body = _list(api, token, q="team", limit=10)
    assert len(body["items"]) == 10 and body["total"] == 30


def test_filters_by_department_status_and_role_and_they_combine_with_the_search(api, make_user, pg):
    token = _admin(api, make_user)
    finance, _ = _ids(pg)
    make_user("fin1@demo")
    make_user("fin2@demo", active=False)
    make_user("eng1@demo")
    make_user("hr1@demo", roles=("employee", "security_admin"))
    pg.execute("UPDATE users SET department_id=%s WHERE email IN ('fin1@demo', 'fin2@demo')", (finance,))

    assert _emails(_list(api, token, department_id=finance)) == ["fin1@demo", "fin2@demo"]
    assert _emails(_list(api, token, is_active="false")) == ["fin2@demo"]
    assert "fin2@demo" not in _emails(_list(api, token, is_active="true"))
    assert _emails(_list(api, token, role="security_admin")) == ["hr1@demo"]
    assert _emails(_list(api, token, role="no_such_role")) == []
    assert _emails(_list(api, token, q="fin", department_id=finance, is_active="true")) == ["fin1@demo"]


def test_a_person_with_several_roles_is_listed_once(api, make_user):
    token = _admin(api, make_user)
    make_user("multi@demo", roles=("employee", "auditor", "security_admin"))
    body = _list(api, token, q="multi")
    assert body["total"] == 1 and len(body["items"]) == 1
    assert _emails(_list(api, token, role="auditor")) == ["multi@demo"]


def test_bad_parameters_are_refused_with_a_clear_422(api, make_user):
    token = _admin(api, make_user)
    for params in ({"limit": 101}, {"limit": 0}, {"offset": -1}, {"q": "x" * 101}, {"is_active": "maybe"}, {"department_id": 0}):
        assert api.request("GET", "/users", token=token, params=params).status_code == 422, params


def test_only_the_administrator_may_search_people(api, make_user):
    make_user("aisha@demo", roles=("employee",))
    make_user("nina@demo", roles=("employee", "auditor"))
    assert api.request("GET", "/users", params={"q": "a"}).status_code == 401
    for email in ("aisha@demo", "nina@demo"):
        token, _ = api.signed_in(email)
        assert api.request("GET", "/users", token=token, params={"q": "a"}).status_code == 403, email
