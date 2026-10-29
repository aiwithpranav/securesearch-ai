"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { ApiError, type Department } from "@/lib/api";
import {
  createUser, deactivateUser, employmentLabel, EMPLOYMENT_TYPES, listRoles, listUsers, pageRange, setUserRoles, updateUser,
  USER_PAGE_SIZE, type Role, type UserItem, type UserStatus,
} from "@/lib/access";
import { listDepartments, SENSITIVITY_LEVELS } from "@/lib/documents";
import { FieldError, FormErrorBox } from "../../../_auth/ui";
import { useSession } from "../../../_auth/AuthProvider";
import { EmptyState, ErrorState, selectClass, TableSkeleton } from "../_components/ui";

const inputClass = "w-full rounded-lg border border-line bg-surface2 px-4 py-3 text-text";

type Form = { email: string; full_name: string; department_id: string; clearance: string; country: string; employment: string; roleIds: number[] };
const emptyForm: Form = { email: "", full_name: "", department_id: "", clearance: "1", country: "IN", employment: "full_time", roleIds: [] };

function Status({ active }: { active: boolean }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${active ? "border-ok/60 text-ok" : "border-line text-muted"}`}>
      {active ? "Active" : "Deactivated"}
    </span>
  );
}

export function UsersView() {
  const { user: me } = useSession();
  const [users, setUsers] = useState<UserItem[] | null>(null);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState(""); // what is typed
  const [q, setQ] = useState(""); // what is searched (after a short pause)
  const [departmentId, setDepartmentId] = useState("");
  const [status, setStatus] = useState<UserStatus>("");
  const [role, setRole] = useState("");
  const latest = useRef(0); // only the newest request may change the list (answers can arrive out of order)
  const [roles, setRoles] = useState<Role[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [error, setError] = useState<{ message: string; requestId?: string } | null>(null);
  const [editing, setEditing] = useState<UserItem | "new" | null>(null);
  const [form, setForm] = useState<Form>(emptyForm);
  const [formError, setFormError] = useState<string | null>(null);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [confirmDeactivate, setConfirmDeactivate] = useState(false);
  const dialogRef = useRef<HTMLDialogElement>(null);

  const load = useCallback(async () => {
    const n = ++latest.current;
    try {
      const page = await listUsers({ offset, q, departmentId, status, role });
      if (n !== latest.current) return;
      if (page.items.length === 0 && page.total > 0 && offset > 0) {
        setOffset(Math.max(0, (Math.ceil(page.total / USER_PAGE_SIZE) - 1) * USER_PAGE_SIZE)); // the page is gone (people were removed): go to the last one
        return;
      }
      setUsers(page.items);
      setTotal(page.total);
      setError(null);
    } catch (e) {
      if (n === latest.current) setError({ message: "The users could not be loaded.", requestId: e instanceof ApiError ? e.requestId : undefined });
    }
  }, [offset, q, departmentId, status, role]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    listRoles().then(setRoles).catch(() => setRoles([]));
    listDepartments().then(setDepartments).catch(() => setDepartments([]));
  }, []);

  // The search starts a moment after the last key, and always from the first page.
  useEffect(() => {
    const timer = setTimeout(() => {
      setQ(search.trim());
      setOffset(0);
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  const filtered = q !== "" || departmentId !== "" || status !== "" || role !== "";
  const range = pageRange(offset, USER_PAGE_SIZE, total);
  function clearFilters() {
    setSearch("");
    setQ("");
    setDepartmentId("");
    setStatus("");
    setRole("");
    setOffset(0);
  }

  function openNew() {
    setForm({ ...emptyForm, department_id: departments[0] ? String(departments[0].id) : "" });
    setEditing("new");
    setFormError(null);
    setEmailError(null);
    setConfirmDeactivate(false);
    dialogRef.current?.showModal();
  }

  function openEdit(u: UserItem) {
    setForm({
      email: u.email, full_name: u.full_name, department_id: String(u.department.id), clearance: String(u.clearance_level),
      country: u.country, employment: u.employment_type, roleIds: roles.filter((r) => u.roles.includes(r.name)).map((r) => r.id),
    });
    setEditing(u);
    setFormError(null);
    setEmailError(null);
    setConfirmDeactivate(false);
    dialogRef.current?.showModal();
  }

  function closeDialog() {
    dialogRef.current?.close();
    setEditing(null);
  }

  async function onSave(e: FormEvent) {
    e.preventDefault();
    if (busy || editing === null) return;
    const emailOk = /^[^@\s]+@[^@\s]+$/.test(form.email.trim());
    if (editing === "new" && !emailOk) {
      setEmailError("Enter a valid email address, like name@company.com.");
      return;
    }
    if (!form.full_name.trim() || !form.department_id || !/^[A-Za-z]{2}$/.test(form.country.trim())) {
      setFormError("Name, department and a 2-letter country code are required.");
      return;
    }
    setBusy(true);
    setFormError(null);
    try {
      const base = {
        full_name: form.full_name.trim(), department_id: Number(form.department_id), clearance_level: Number(form.clearance),
        country: form.country.trim().toUpperCase(), employment_type: form.employment,
      };
      if (editing === "new") {
        await createUser({ ...base, email: form.email.trim(), role_ids: form.roleIds });
        setNotice(`Invitation sent to ${form.email.trim()}. The person sets a password from the emailed link.`);
      } else {
        await updateUser(editing.id, base);
        await setUserRoles(editing.id, form.roleIds);
        setNotice(`Saved changes for ${form.full_name.trim()}.`);
      }
      closeDialog();
      await load();
    } catch (err) {
      setFormError(
        err instanceof ApiError && (err.status === 409 || err.status === 400 || err.status === 422) ? err.message : "The changes could not be saved.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function onToggleActive(u: UserItem) {
    setBusy(true);
    setFormError(null);
    try {
      if (u.is_active) await deactivateUser(u.id);
      else await updateUser(u.id, { is_active: true });
      setNotice(`${u.full_name} is now ${u.is_active ? "deactivated and signed out everywhere" : "active again"}.`);
      closeDialog();
      await load();
    } catch (err) {
      setFormError(err instanceof ApiError && err.status === 400 ? err.message : "The change could not be saved.");
    } finally {
      setBusy(false);
      setConfirmDeactivate(false);
    }
  }

  const isSelf = editing !== null && editing !== "new" && editing.id === me?.id;
  const adminRoleId = roles.find((r) => r.name === "system_admin")?.id;

  return (
    <main id="main" className="mx-auto w-full max-w-6xl px-5 py-12">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Users</h1>
          <p className="mt-2 text-muted">Invite people, set their department, clearance and roles. Managing users does not give access to documents.</p>
          {users && <p className="mt-1 text-sm text-muted" aria-live="polite">{filtered ? `${total} ${total === 1 ? "person matches" : "people match"} your search and filters` : `${total} ${total === 1 ? "person" : "people"}`}</p>}
        </div>
        <button type="button" onClick={openNew} className="rounded-lg bg-accent px-5 py-3 font-medium text-bg hover:bg-accent2">Invite user</button>
      </div>

      {notice && <p role="status" className="mt-6 rounded-lg border border-ok/60 bg-ok/10 p-3 text-sm text-ok">{notice}</p>}

      <div role="search" aria-label="Find people" className="mt-8 flex flex-wrap items-end gap-4">
        <div className="min-w-[14rem] flex-1">
          <label htmlFor="f-search" className="mb-1 block text-sm text-muted">Search by name or email</label>
          <input id="f-search" type="search" className={selectClass} value={search} maxLength={100} autoComplete="off"
            placeholder="For example: meera" onChange={(e) => setSearch(e.target.value)} />
        </div>
        <div>
          <label htmlFor="f-dept" className="mb-1 block text-sm text-muted">Department</label>
          <select id="f-dept" className={selectClass} value={departmentId} onChange={(e) => { setOffset(0); setDepartmentId(e.target.value); }}>
            <option value="">All</option>
            {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="f-role" className="mb-1 block text-sm text-muted">Role</label>
          <select id="f-role" className={selectClass} value={role} onChange={(e) => { setOffset(0); setRole(e.target.value); }}>
            <option value="">All</option>
            {roles.map((r) => <option key={r.id} value={r.name}>{r.name}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="f-status" className="mb-1 block text-sm text-muted">Status</label>
          <select id="f-status" className={selectClass} value={status} onChange={(e) => { setOffset(0); setStatus(e.target.value as UserStatus); }}>
            <option value="">All</option>
            <option value="active">Active</option>
            <option value="inactive">Deactivated</option>
          </select>
        </div>
        {filtered && <button type="button" onClick={clearFilters} className="rounded-lg border border-line px-4 py-3 text-sm hover:border-accent2">Clear</button>}
      </div>

      <div className="mt-6" aria-live="polite">
        {error && !users ? <ErrorState message={error.message} requestId={error.requestId} onRetry={() => void load()} />
          : !users ? <TableSkeleton />
          : users.length === 0 ? (filtered ? <EmptyState title="No one matches" text="Try a different name or clear the filters." /> : <EmptyState title="No users" text="Invite the first user." />)
          : (
            <div className="relative overflow-x-auto rounded-2xl border border-line">
              <table className="w-full min-w-[860px] text-left text-sm">
                <caption className="sr-only">Users</caption>
                <thead className="bg-surface text-muted"><tr>
                  <th scope="col" className="px-4 py-3 font-medium">Name</th>
                  <th scope="col" className="px-4 py-3 font-medium">Department</th>
                  <th scope="col" className="px-4 py-3 font-medium">Roles</th>
                  <th scope="col" className="px-4 py-3 font-medium">Clearance</th>
                  <th scope="col" className="px-4 py-3 font-medium">Country</th>
                  <th scope="col" className="px-4 py-3 font-medium">Status</th>
                  <th scope="col" className="px-4 py-3"><span className="sr-only">Actions</span></th>
                </tr></thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id} className="border-t border-line align-top">
                      <td className="px-4 py-3"><div className="font-medium">{u.full_name}</div><div className="text-xs text-muted">{u.email}</div></td>
                      <td className="px-4 py-3">{u.department.name}</td>
                      <td className="px-4 py-3"><div className="flex max-w-xs flex-wrap gap-1">{u.roles.map((r) => <span key={r} className="rounded-full border border-line bg-surface2 px-2 py-0.5 text-xs">{r}</span>)}</div></td>
                      <td className="px-4 py-3 tabular-nums">{u.clearance_level}</td>
                      <td className="px-4 py-3">{u.country}</td>
                      <td className="px-4 py-3"><Status active={u.is_active} /></td>
                      <td className="px-4 py-3 text-right">
                        <button type="button" onClick={() => openEdit(u)} aria-label={`Edit ${u.full_name}`} className="rounded-lg border border-line px-3 py-1.5 hover:border-accent2">Edit</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        {users && total > 0 && (
          <nav aria-label="Pages of people" className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm">
            <span className="text-muted">{range.from} to {range.to} of {total}</span>
            <span className="flex gap-2">
              <button type="button" disabled={!range.hasPrevious} onClick={() => setOffset(Math.max(0, offset - USER_PAGE_SIZE))}
                className="rounded-lg border border-line px-4 py-2 hover:border-accent2 disabled:opacity-50">Previous</button>
              <button type="button" disabled={!range.hasNext} onClick={() => setOffset(offset + USER_PAGE_SIZE)}
                className="rounded-lg border border-line px-4 py-2 hover:border-accent2 disabled:opacity-50">Next</button>
            </span>
          </nav>
        )}
      </div>

      <dialog ref={dialogRef} onClose={() => setEditing(null)} aria-labelledby="user-dialog-title"
        className="m-auto w-[calc(100%-2rem)] max-w-xl rounded-2xl border border-line bg-surface p-6 text-text backdrop:bg-bg/80">
        {editing !== null && (
          <form onSubmit={onSave} noValidate className="space-y-4">
            <h2 id="user-dialog-title" className="text-xl font-semibold">{editing === "new" ? "Invite user" : `Edit ${editing.full_name}`}</h2>
            {formError && <FormErrorBox message={formError} />}
            <div>
              <label htmlFor="u-email" className="mb-1 block text-sm font-medium">Email</label>
              <input id="u-email" type="email" className={inputClass} value={form.email} disabled={editing !== "new"} autoComplete="off"
                aria-invalid={emailError ? true : undefined} aria-describedby={emailError ? "u-email-error" : undefined}
                onChange={(e) => { setForm({ ...form, email: e.target.value }); setEmailError(null); }} />
              {emailError && <FieldError id="u-email-error" message={emailError} />}
            </div>
            <div>
              <label htmlFor="u-name" className="mb-1 block text-sm font-medium">Full name</label>
              <input id="u-name" className={inputClass} value={form.full_name} maxLength={120} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="u-dept" className="mb-1 block text-sm font-medium">Department</label>
                <select id="u-dept" className={selectClass} value={form.department_id} onChange={(e) => setForm({ ...form, department_id: e.target.value })}>
                  {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                </select>
              </div>
              <div>
                <label htmlFor="u-clear" className="mb-1 block text-sm font-medium">Clearance level</label>
                <select id="u-clear" className={selectClass} value={form.clearance} onChange={(e) => setForm({ ...form, clearance: e.target.value })}>
                  {SENSITIVITY_LEVELS.map((s) => <option key={s.value} value={s.value}>{s.value} · {s.name.replace("_", " ")}</option>)}
                </select>
              </div>
              <div>
                <label htmlFor="u-country" className="mb-1 block text-sm font-medium">Country (2 letters)</label>
                <input id="u-country" className={inputClass} value={form.country} maxLength={2} onChange={(e) => setForm({ ...form, country: e.target.value })} />
              </div>
              <div>
                <label htmlFor="u-emp" className="mb-1 block text-sm font-medium">Employment</label>
                <select id="u-emp" className={selectClass} value={form.employment} onChange={(e) => setForm({ ...form, employment: e.target.value })}>
                  {EMPLOYMENT_TYPES.map((t) => <option key={t} value={t}>{employmentLabel(t)}</option>)}
                </select>
              </div>
            </div>
            <fieldset>
              <legend className="mb-2 text-sm font-medium">Roles</legend>
              <div className="grid gap-2 sm:grid-cols-2">
                {roles.map((r) => {
                  const lockAdmin = isSelf && r.id === adminRoleId; // you cannot remove your own admin role
                  return (
                    <label key={r.id} className="flex items-center gap-2 text-sm">
                      <input type="checkbox" className="h-4 w-4 accent-accent" checked={form.roleIds.includes(r.id)} disabled={lockAdmin}
                        onChange={(e) => setForm({ ...form, roleIds: e.target.checked ? [...form.roleIds, r.id] : form.roleIds.filter((x) => x !== r.id) })} />
                      {r.name}{lockAdmin && <span className="text-xs text-muted">(your own)</span>}
                    </label>
                  );
                })}
              </div>
              <p className="mt-2 text-xs text-muted">Roles are used in access rules. The system_admin role manages accounts and rules but never gives permission to read documents.</p>
            </fieldset>

            <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
              <div className="flex gap-3">
                <button type="submit" disabled={busy} className="rounded-lg bg-accent px-5 py-2.5 font-medium text-bg hover:bg-accent2 disabled:opacity-70">
                  {busy ? "Saving…" : editing === "new" ? "Send invitation" : "Save"}
                </button>
                <button type="button" onClick={closeDialog} disabled={busy} className="rounded-lg border border-line px-5 py-2.5 hover:border-accent2">Cancel</button>
              </div>
              {editing !== "new" && !isSelf && (
                !confirmDeactivate ? (
                  <button type="button" onClick={() => setConfirmDeactivate(true)} disabled={busy}
                    className={`rounded-lg border px-4 py-2.5 text-sm ${editing.is_active ? "border-bad/60 text-bad hover:bg-bad/10" : "border-line hover:border-accent2"}`}>
                    {editing.is_active ? "Deactivate" : "Reactivate"}
                  </button>
                ) : (
                  <span className="flex items-center gap-2 text-sm" role="group" aria-label="Confirm">
                    {editing.is_active ? "Sign them out and block login?" : "Allow login again?"}
                    <button type="button" autoFocus onClick={() => onToggleActive(editing)} disabled={busy} className="rounded-lg bg-accent px-3 py-1.5 font-medium text-bg">Yes</button>
                    <button type="button" onClick={() => setConfirmDeactivate(false)} className="rounded-lg border border-line px-3 py-1.5">No</button>
                  </span>
                )
              )}
            </div>
          </form>
        )}
      </dialog>
    </main>
  );
}
