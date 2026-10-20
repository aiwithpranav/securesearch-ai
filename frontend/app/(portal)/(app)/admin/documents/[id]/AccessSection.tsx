"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { ApiError, type Department } from "@/lib/api";
import {
  accessPreview, addRule, deleteRule, describeRule, diffRules, EFFECT_LABELS, expiryText, listGroups, listRoles, listRules,
  listUsers, localInputToIso, PERMISSION_LABELS, PRINCIPAL_TYPES, reasonText, ruleHistory, updateRule,
  type Effect, type Group, type HistoryItem, type Permission, type Preview, type PrincipalType, type Role, type Rule, type SnapshotRule, type UserItem,
} from "@/lib/access";
import { formatDateTime, listDepartments } from "@/lib/documents";
import { FieldError, FormErrorBox } from "../../../../_auth/ui";
import { selectClass } from "../../_components/ui";

const card = "rounded-2xl border border-line bg-surface p-6";

function EffectBadge({ effect }: { effect: Effect }) {
  return (
    <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-medium ${effect === "ALLOW" ? "border-ok/60 text-ok" : "border-bad/60 text-bad"}`}>
      {effect === "ALLOW" ? "✓ Allow" : "✕ Deny"}
    </span>
  );
}

export function AccessSection({ documentId }: { documentId: string }) {
  const [rules, setRules] = useState<Rule[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [users, setUsers] = useState<UserItem[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [busy, setBusy] = useState(false);

  // add-rule form
  const [ptype, setPtype] = useState<PrincipalType>("GROUP");
  const [pid, setPid] = useState("");
  const [effect, setEffect] = useState<Effect>("ALLOW");
  const [permission, setPermission] = useState<Permission>("READ");
  const [expires, setExpires] = useState("");
  const [pidError, setPidError] = useState<string | null>(null);
  const [expiresError, setExpiresError] = useState<string | null>(null);
  const [confirmDeny, setConfirmDeny] = useState(false);

  // edit and delete
  const [editId, setEditId] = useState<string | null>(null);
  const [edit, setEdit] = useState<{ effect: Effect; permission: Permission; expires: string }>({ effect: "ALLOW", permission: "READ", expires: "" });
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  // history and preview
  const [history, setHistory] = useState<HistoryItem[] | null>(null);
  const [previewUser, setPreviewUser] = useState("");
  const [preview, setPreview] = useState<Preview | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setRules(await listRules(documentId));
      setError(null);
    } catch {
      setError("The access rules could not be loaded.");
    }
  }, [documentId]);

  useEffect(() => {
    void load();
    listUsers().then((p) => setUsers(p.items)).catch(() => setUsers([]));
    listRoles().then(setRoles).catch(() => setRoles([]));
    listGroups().then(setGroups).catch(() => setGroups([]));
    listDepartments().then(setDepartments).catch(() => setDepartments([]));
  }, [load]);

  const principalOptions: { value: string; label: string }[] =
    ptype === "USER" ? users.map((u) => ({ value: u.id, label: `${u.full_name} (${u.email})` }))
    : ptype === "ROLE" ? roles.map((r) => ({ value: String(r.id), label: r.name }))
    : ptype === "GROUP" ? groups.map((g) => ({ value: String(g.id), label: g.name }))
    : ptype === "DEPARTMENT" ? departments.map((d) => ({ value: String(d.id), label: d.name }))
    : [];

  /** History snapshots hold ids only: look the name up in the lists already loaded. */
  function snapshotName(r: SnapshotRule): string {
    if (r.principal_name) return r.principal_name;
    if (r.principal_type === "COMPANY") return "Everyone";
    const id = String(r.principal_id);
    const found =
      r.principal_type === "USER" ? users.find((u) => u.id === id)?.full_name
      : r.principal_type === "ROLE" ? roles.find((x) => String(x.id) === id)?.name
      : r.principal_type === "GROUP" ? groups.find((g) => String(g.id) === id)?.name
      : departments.find((d) => String(d.id) === id)?.name;
    return found ?? "(no longer exists)";
  }
  const describeSnapshot = (r: SnapshotRule) => describeRule({ ...r, principal_name: snapshotName(r) });

  async function refreshAfterChange() {
    setHistory(null);
    setPreview(null);
    await load();
  }

  async function onAdd(e: FormEvent) {
    e.preventDefault();
    if (busy) return;
    if (ptype !== "COMPANY" && !pid) { setPidError("Please choose who the rule is about."); return; }
    const iso = localInputToIso(expires);
    if (expires && iso && new Date(iso).getTime() <= Date.now()) { setExpiresError("The expiry must be in the future."); return; }
    if (effect === "DENY" && !confirmDeny) { setConfirmDeny(true); return; } // a Deny always wins: ask once
    setBusy(true);
    setActionError(null);
    try {
      await addRule(documentId, { principal_type: ptype, principal_id: ptype === "COMPANY" ? null : pid, effect, permission, expires_at: iso });
      setPid("");
      setExpires("");
      setConfirmDeny(false);
      await refreshAfterChange();
    } catch (err) {
      setConfirmDeny(false);
      setActionError(err instanceof ApiError && [409, 422].includes(err.status) ? err.message : "The rule could not be added.");
    } finally {
      setBusy(false);
    }
  }

  function startEdit(r: Rule) {
    setEditId(r.id);
    setEdit({ effect: r.effect, permission: r.permission, expires: r.expires_at ? toLocalInput(r.expires_at) : "" });
    setActionError(null);
  }

  async function onSaveEdit(r: Rule) {
    const iso = localInputToIso(edit.expires);
    if (edit.expires && iso && new Date(iso).getTime() <= Date.now()) { setActionError("The expiry must be in the future."); return; }
    setBusy(true);
    setActionError(null);
    try {
      await updateRule(documentId, r.id, { effect: edit.effect, permission: edit.permission, expires_at: iso });
      setEditId(null);
      await refreshAfterChange();
    } catch (err) {
      setActionError(err instanceof ApiError && [409, 422].includes(err.status) ? err.message : "The rule could not be changed.");
    } finally {
      setBusy(false);
    }
  }

  async function onDelete(r: Rule) {
    setBusy(true);
    setActionError(null);
    try {
      await deleteRule(documentId, r.id);
      setConfirmDelete(null);
      await refreshAfterChange();
    } catch {
      setActionError("The rule could not be removed.");
    } finally {
      setBusy(false);
    }
  }

  async function onToggleHistory(open: boolean) {
    if (open && history === null) {
      try { setHistory(await ruleHistory(documentId)); } catch { setHistory([]); }
    }
  }

  async function onPreview() {
    if (!previewUser) return;
    setPreviewError(null);
    try {
      setPreview(await accessPreview(documentId, previewUser));
    } catch {
      setPreview(null);
      setPreviewError("The preview could not be loaded.");
    }
  }

  return (
    <section className={`${card} mt-8`} aria-labelledby="access-title">
      <h2 id="access-title" className="text-xl font-semibold">Access</h2>
      <p className="mt-2 text-sm text-muted">
        Nobody can read this document unless a rule allows it. A Deny rule always wins over an Allow. People also need a clearance level at least as high as the document&apos;s sensitivity.
      </p>
      {actionError && <div className="mt-4"><FormErrorBox message={actionError} /></div>}

      <div className="mt-6" aria-live="polite">
        {error && !rules ? <p role="alert" className="text-bad">{error}</p>
          : !rules ? <p className="text-muted">Loading rules…</p>
          : rules.length === 0 ? <p className="rounded-lg border border-dashed border-line p-4 text-muted">No rules yet: nobody can read this document.</p>
          : (
            <div className="relative overflow-x-auto">
              <table className="w-full min-w-[640px] text-left text-sm">
                <caption className="sr-only">Access rules</caption>
                <thead className="text-muted"><tr>
                  <th scope="col" className="py-2 pr-4 font-medium">Who</th>
                  <th scope="col" className="py-2 pr-4 font-medium">Rule</th>
                  <th scope="col" className="py-2 pr-4 font-medium">Until</th>
                  <th scope="col" className="py-2"><span className="sr-only">Actions</span></th>
                </tr></thead>
                <tbody>
                  {rules.map((r) => (
                    <tr key={r.id} className="border-t border-line align-top">
                      <td className="py-3 pr-4"><div className="font-medium">{r.principal_name}</div><div className="text-xs text-muted">{PRINCIPAL_TYPES.find((t) => t.value === r.principal_type)?.label}</div></td>
                      {editId === r.id ? (
                        <td colSpan={2} className="py-3 pr-4">
                          <div className="flex flex-wrap items-end gap-3">
                            <label className="text-xs text-muted">Effect
                              <select className={`${selectClass} mt-1`} value={edit.effect} onChange={(e) => setEdit({ ...edit, effect: e.target.value as Effect })}>
                                <option value="ALLOW">Allow</option><option value="DENY">Deny</option>
                              </select></label>
                            <label className="text-xs text-muted">Permission
                              <select className={`${selectClass} mt-1`} value={edit.permission} onChange={(e) => setEdit({ ...edit, permission: e.target.value as Permission })}>
                                {(Object.keys(PERMISSION_LABELS) as Permission[]).map((p) => <option key={p} value={p}>{PERMISSION_LABELS[p]}</option>)}
                              </select></label>
                            <label className="text-xs text-muted">Expires
                              <input type="datetime-local" className={`${selectClass} mt-1`} value={edit.expires} onChange={(e) => setEdit({ ...edit, expires: e.target.value })} /></label>
                          </div>
                        </td>
                      ) : (
                        <>
                          <td className="py-3 pr-4"><div className="flex flex-wrap items-center gap-2"><EffectBadge effect={r.effect} /><span>{PERMISSION_LABELS[r.permission]}</span></div></td>
                          <td className={`py-3 pr-4 ${r.expired ? "text-bad" : "text-muted"}`}>{expiryText(r)}</td>
                        </>
                      )}
                      <td className="py-3 text-right">
                        {editId === r.id ? (
                          <span className="flex justify-end gap-2">
                            <button type="button" onClick={() => void onSaveEdit(r)} disabled={busy} className="rounded-lg bg-accent px-3 py-1.5 font-medium text-bg">Save</button>
                            <button type="button" onClick={() => setEditId(null)} className="rounded-lg border border-line px-3 py-1.5">Cancel</button>
                          </span>
                        ) : confirmDelete === r.id ? (
                          <span className="flex flex-wrap justify-end items-center gap-2" role="group" aria-label="Confirm remove rule">
                            Remove this rule?
                            <button type="button" autoFocus onClick={() => void onDelete(r)} disabled={busy} className="rounded-lg bg-bad px-3 py-1.5 font-medium text-bg">Yes</button>
                            <button type="button" onClick={() => setConfirmDelete(null)} className="rounded-lg border border-line px-3 py-1.5">No</button>
                          </span>
                        ) : (
                          <span className="flex justify-end gap-2">
                            <button type="button" onClick={() => startEdit(r)} aria-label={`Edit rule: ${describeRule(r)}`} className="rounded-lg border border-line px-3 py-1.5 hover:border-accent2">Edit</button>
                            <button type="button" onClick={() => setConfirmDelete(r.id)} aria-label={`Remove rule: ${describeRule(r)}`} className="rounded-lg border border-line px-3 py-1.5 hover:border-bad/60">Remove</button>
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
      </div>

      <form onSubmit={onAdd} noValidate className="mt-8 rounded-xl border border-line p-5" aria-labelledby="add-rule-title">
        <h3 id="add-rule-title" className="font-semibold">Add a rule</h3>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="r-type" className="mb-1 block text-sm font-medium">This rule is about</label>
            <select id="r-type" className={selectClass} value={ptype} onChange={(e) => { setPtype(e.target.value as PrincipalType); setPid(""); setPidError(null); }}>
              {PRINCIPAL_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </div>
          {ptype !== "COMPANY" && (
            <div>
              <label htmlFor="r-who" className="mb-1 block text-sm font-medium">Who</label>
              <select id="r-who" className={`${selectClass} ${pidError ? "border-bad" : ""}`} value={pid} aria-invalid={pidError ? true : undefined}
                aria-describedby={pidError ? "r-who-error" : undefined} onChange={(e) => { setPid(e.target.value); setPidError(null); }}>
                <option value="">Choose...</option>
                {principalOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
              {pidError && <FieldError id="r-who-error" message={pidError} />}
            </div>
          )}
          <div>
            <label htmlFor="r-effect" className="mb-1 block text-sm font-medium">Effect</label>
            <select id="r-effect" className={selectClass} value={effect} onChange={(e) => { setEffect(e.target.value as Effect); setConfirmDeny(false); }}>
              {(Object.keys(EFFECT_LABELS) as Effect[]).map((x) => <option key={x} value={x}>{EFFECT_LABELS[x]}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="r-perm" className="mb-1 block text-sm font-medium">Permission</label>
            <select id="r-perm" className={selectClass} value={permission} onChange={(e) => setPermission(e.target.value as Permission)}>
              {(Object.keys(PERMISSION_LABELS) as Permission[]).map((p) => <option key={p} value={p}>{PERMISSION_LABELS[p]}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="r-exp" className="mb-1 block text-sm font-medium">Expires <span className="text-muted">(optional)</span></label>
            <input id="r-exp" type="datetime-local" className={`${selectClass} ${expiresError ? "border-bad" : ""}`} value={expires}
              aria-invalid={expiresError ? true : undefined} aria-describedby={expiresError ? "r-exp-error" : undefined}
              onChange={(e) => { setExpires(e.target.value); setExpiresError(null); }} />
            {expiresError && <FieldError id="r-exp-error" message={expiresError} />}
          </div>
        </div>
        {permission === "MANAGE" && (
          <p className="mt-4 text-sm text-muted">&ldquo;Can manage&rdquo; lets a person change this document&apos;s rules and details. It does <strong>not</strong> let them read the document.</p>
        )}
        {confirmDeny && (
          <p role="alert" className="mt-4 rounded-lg border border-bad/60 bg-bad/10 p-3 text-sm text-bad">
            A Deny rule always wins over any Allow. Press <strong>Confirm Deny</strong> to add it.
          </p>
        )}
        <button type="submit" disabled={busy} className={`mt-4 rounded-lg px-5 py-2.5 font-medium text-bg disabled:opacity-70 ${confirmDeny ? "bg-bad" : "bg-accent hover:bg-accent2"}`}>
          {confirmDeny ? "Confirm Deny" : "Add rule"}
        </button>
      </form>

      <div className="mt-8 rounded-xl border border-line p-5">
        <h3 className="font-semibold">Who can read this? (preview)</h3>
        <div className="mt-3 flex flex-wrap items-end gap-3">
          <div className="min-w-[14rem] flex-1">
            <label htmlFor="p-user" className="mb-1 block text-sm font-medium">Person</label>
            <select id="p-user" className={selectClass} value={previewUser} onChange={(e) => { setPreviewUser(e.target.value); setPreview(null); }}>
              <option value="">Choose...</option>
              {users.map((u) => <option key={u.id} value={u.id}>{u.full_name} ({u.email})</option>)}
            </select>
          </div>
          <button type="button" onClick={() => void onPreview()} disabled={!previewUser} className="rounded-lg border border-line px-5 py-3 hover:border-accent2 disabled:opacity-50">Check access</button>
        </div>
        <div aria-live="polite">
          {previewError && <p role="alert" className="mt-3 text-sm text-bad">{previewError}</p>}
          {preview && (
            <div className="mt-4 space-y-3 text-sm">
              <p className="text-muted">
                {preview.user.full_name}: {preview.user.department.name}, clearance {preview.user.clearance_level}, country {preview.user.country}. Document sensitivity {preview.sensitivity_level}.
              </p>
              {([["Read", preview.read], ["Download", preview.download], ["Manage", preview.manage]] as const).map(([label, d]) => (
                <div key={label} className="flex flex-wrap items-start gap-3 rounded-lg border border-line p-3">
                  <span className={`inline-flex min-w-[5.5rem] justify-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${d.allowed ? "border-ok/60 text-ok" : "border-bad/60 text-bad"}`}>
                    {d.allowed ? "✓ " : "✕ "}{label}
                  </span>
                  <span>{reasonText(d.code)}</span>
                </div>
              ))}
              {preview.matching_rules.length > 0 && (
                <div>
                  <p className="font-medium">Rules that apply to this person</p>
                  <ul className="mt-1 list-disc pl-5 text-muted">{preview.matching_rules.map((r) => <li key={r.id}>{describeRule(r)}</li>)}</ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <details className="mt-8 rounded-xl border border-line p-5" onToggle={(e) => void onToggleHistory((e.currentTarget as HTMLDetailsElement).open)}>
        <summary className="cursor-pointer font-semibold">History of changes</summary>
        <div className="mt-4 space-y-4 text-sm">
          {history === null ? <p className="text-muted">Loading…</p> : history.length === 0 ? <p className="text-muted">No changes recorded yet.</p> : history.map((h) => {
            const d = diffRules(h.prev_acl, h.new_acl);
            return (
              <div key={h.id} className="rounded-lg border border-line p-3">
                <p className="text-muted">{formatDateTime(h.changed_at)} · {h.changed_by ? h.changed_by.full_name : "System (seed)"}</p>
                <ul className="mt-1 list-disc pl-5">
                  {d.added.map((r) => <li key={`a${r.id}`}>Added: {describeSnapshot(r)}</li>)}
                  {d.removed.map((r) => <li key={`r${r.id}`}>Removed: {describeSnapshot(r)}</li>)}
                  {d.changed.map((r) => <li key={`c${r.id}`}>Changed to: {describeSnapshot(r)}</li>)}
                </ul>
                <p className="mt-1 text-xs text-muted">{h.prev_acl.length} rule(s) before, {h.new_acl.length} after.</p>
              </div>
            );
          })}
        </div>
      </details>
    </section>
  );
}

/** ISO time to the value format of <input type="datetime-local"> (local time, no seconds). */
function toLocalInput(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
