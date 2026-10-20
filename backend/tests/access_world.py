"""A tiny 'world' builder for access tests: users, groups, documents and rules written straight into the
test database, so each test can describe a situation in two or three lines."""
import uuid


class World:
    def __init__(self, pg):
        self.pg = pg
        self._n = 0
        self.uploader = self.user("uploader@w", dept="Engineering", clearance=4, roles=("system_admin",))

    # ---- ids
    def dept_id(self, name):
        return self.pg.execute("select id from departments where name=%s", (name,)).fetchone()[0]

    def role_id(self, name):
        row = self.pg.execute("select id from roles where name=%s", (name,)).fetchone()
        if row:
            return row[0]
        return self.pg.execute("insert into roles (name) values (%s) returning id", (name,)).fetchone()[0]

    def group_id(self, name):
        row = self.pg.execute("select id from groups where name=%s", (name,)).fetchone()
        if row:
            return row[0]
        return self.pg.execute("insert into groups (name) values (%s) returning id", (name,)).fetchone()[0]

    # ---- building blocks
    def user(self, email=None, dept="Engineering", clearance=2, country="IN", active=True, roles=(), groups=()):
        self._n += 1
        email = email or f"user{self._n}@w"
        uid = self.pg.execute(
            "insert into users (email, full_name, password_hash, department_id, clearance_level, country, is_active) "
            "values (%s,%s,'x',%s,%s,%s,%s) returning id",
            (email, email, self.dept_id(dept), clearance, country, active),
        ).fetchone()[0]
        for r in roles:
            self.pg.execute("insert into user_roles values (%s,%s)", (uid, self.role_id(r)))
        for g in groups:
            self.pg.execute("insert into user_groups (user_id, group_id) values (%s,%s)", (uid, self.group_id(g)))
        return uid

    def doc(self, sensitivity=1, status="READY", countries=None, deleted=False, dept="Engineering"):
        did = self.pg.execute(
            "insert into documents (title, original_filename, document_type, department_id, sensitivity_level, status,"
            " allowed_countries, uploaded_by, deleted_at) values ('t','t.txt','POLICY',%s,%s,%s,%s,%s,"
            " case when %s then now() else null end) returning id",
            (self.dept_id(dept), sensitivity, status, countries, self.uploader, deleted),
        ).fetchone()[0]
        return did

    def acl(self, doc, principal, effect="ALLOW", permission="READ", expires=None):
        """principal: ("USER", user_id) | ("ROLE", name) | ("GROUP", name) | ("DEPARTMENT", name) | ("COMPANY", None).
        expires: None or a Postgres interval text such as '1 hour' or '-1 hour' (relative to now)."""
        ptype, who = principal
        pid = {
            "USER": lambda: str(who),
            "ROLE": lambda: str(self.role_id(who)),
            "GROUP": lambda: str(self.group_id(who)),
            "DEPARTMENT": lambda: str(self.dept_id(who)),
            "COMPANY": lambda: None,
        }[ptype]()
        self.pg.execute(
            "insert into document_acl (document_id, principal_type, principal_id, effect, permission, expires_at)"
            " values (%s,%s,%s,%s,%s, case when %s::text is null then null else now() + %s::interval end)",
            (doc, ptype, pid, effect, permission, expires, expires),
        )

    # ---- changes after the fact
    def remove_from_group(self, user, group):
        self.pg.execute("delete from user_groups where user_id=%s and group_id=%s", (user, self.group_id(group)))

    def move_to_department(self, user, dept):
        self.pg.execute("update users set department_id=%s where id=%s", (self.dept_id(dept), user))


def new_id() -> uuid.UUID:
    return uuid.uuid4()
