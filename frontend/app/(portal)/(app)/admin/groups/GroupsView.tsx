"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { ApiError } from "@/lib/api";
import { addMember, createGroup, getGroup, listGroups, listUsers, removeMember, type Group, type GroupDetail, type UserItem } from "@/lib/access";
import { FieldError, FormErrorBox } from "../../../_auth/ui";
import { EmptyState, ErrorState, selectClass, TableSkeleton } from "../_components/ui";

const inputClass = "w-full rounded-lg border border-line bg-surface2 px-4 py-3 text-text";

export function GroupsView() {
  const [groups, setGroups] = useState<Group[] | null>(null);
  const [users, setUsers] = useState<UserItem[]>([]);
  const [selected, setSelected] = useState<GroupDetail | null>(null);
  const [error, setError] = useState<{ message: string; requestId?: string } | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [nameError, setNameError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [toAdd, setToAdd] = useState("");
  const [confirmRemove, setConfirmRemove] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setGroups(await listGroups());
      setError(null);
    } catch (e) {
      setError({ message: "The groups could not be loaded.", requestId: e instanceof ApiError ? e.requestId : undefined });
    }
  }, []);

  useEffect(() => {
    void load();
    listUsers().then((p) => setUsers(p.items)).catch(() => setUsers([]));
  }, [load]);

  async function open(id: number) {
    setActionError(null);
    setConfirmRemove(null);
    try {
      setSelected(await getGroup(id));
    } catch {
      setActionError("The group could not be loaded.");
    }
  }

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    if (busy) return;
    if (name.trim().length < 2) {
      setNameError("The group name needs at least 2 characters.");
      return;
    }
    setBusy(true);
    setActionError(null);
    try {
      const g = await createGroup(name.trim(), description.trim() || null);
      setName("");
      setDescription("");
      setNameError(null);
      await load();
      await open(g.id);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) setNameError("A group with this name already exists.");
      else setActionError("The group could not be created.");
    } finally {
      setBusy(false);
    }
  }

  async function onAdd() {
    if (!selected || !toAdd || busy) return;
    setBusy(true);
    setActionError(null);
    try {
      setSelected(await addMember(selected.id, toAdd));
      setToAdd("");
      await load();
    } catch {
      setActionError("The person could not be added.");
    } finally {
      setBusy(false);
    }
  }

  async function onRemove(userId: string) {
    if (!selected) return;
    setBusy(true);
    setActionError(null);
    try {
      await removeMember(selected.id, userId);
      setConfirmRemove(null);
      setSelected(await getGroup(selected.id));
      await load();
    } catch {
      setActionError("The person could not be removed.");
    } finally {
      setBusy(false);
    }
  }

  const candidates = users.filter((u) => u.is_active && !selected?.members.some((m) => m.id === u.id));

  return (
    <main id="main" className="mx-auto w-full max-w-6xl px-5 py-12">
      <h1 className="text-3xl font-semibold tracking-tight">Groups</h1>
      <p className="mt-2 text-muted">Groups let you give or deny access to many people at once. Removing someone from a group takes effect on their next request.</p>

      <div className="mt-8 grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
        <section aria-labelledby="g-list">
          <h2 id="g-list" className="text-xl font-semibold">All groups</h2>
          <div className="mt-4" aria-live="polite">
            {error && !groups ? <ErrorState message={error.message} requestId={error.requestId} onRetry={() => void load()} />
              : !groups ? <TableSkeleton rows={3} />
              : groups.length === 0 ? <EmptyState title="No groups yet" text="Create the first group below." />
              : (
                <ul className="space-y-2">
                  {groups.map((g) => (
                    <li key={g.id}>
                      <button type="button" onClick={() => void open(g.id)} aria-current={selected?.id === g.id ? "true" : undefined}
                        className={`flex w-full items-center justify-between rounded-xl border px-4 py-3 text-left ${selected?.id === g.id ? "border-accent2 bg-surface" : "border-line hover:border-accent2"}`}>
                        <span className="font-medium">{g.name}</span>
                        <span className="text-sm text-muted">{g.member_count} {g.member_count === 1 ? "member" : "members"}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
          </div>

          <form onSubmit={onCreate} noValidate className="mt-6 rounded-2xl border border-line bg-surface p-5">
            <h3 className="font-semibold">New group</h3>
            <div className="mt-3">
              <label htmlFor="g-name" className="mb-1 block text-sm font-medium">Name</label>
              <input id="g-name" className={`${inputClass} ${nameError ? "border-bad" : ""}`} value={name} maxLength={60}
                aria-invalid={nameError ? true : undefined} aria-describedby={nameError ? "g-name-error" : undefined}
                onChange={(e) => { setName(e.target.value); setNameError(null); }} />
              {nameError && <FieldError id="g-name-error" message={nameError} />}
            </div>
            <div className="mt-3">
              <label htmlFor="g-desc" className="mb-1 block text-sm font-medium">Description <span className="text-muted">(optional)</span></label>
              <input id="g-desc" className={inputClass} value={description} maxLength={200} onChange={(e) => setDescription(e.target.value)} />
            </div>
            <button type="submit" disabled={busy} className="mt-4 rounded-lg bg-accent px-5 py-2.5 font-medium text-bg hover:bg-accent2 disabled:opacity-70">Create group</button>
          </form>
        </section>

        <section aria-labelledby="g-detail">
          <h2 id="g-detail" className="text-xl font-semibold">{selected ? selected.name : "Members"}</h2>
          {actionError && <div className="mt-4"><FormErrorBox message={actionError} /></div>}
          {!selected ? (
            <p className="mt-4 text-muted">Choose a group to see and change its members.</p>
          ) : (
            <div className="mt-4 rounded-2xl border border-line bg-surface p-5">
              {selected.description && <p className="mb-4 text-sm text-muted">{selected.description}</p>}
              {selected.members.length === 0 ? <p className="text-muted">This group has no members yet.</p> : (
                <ul className="divide-y divide-line">
                  {selected.members.map((m) => (
                    <li key={m.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                      <div><div className="font-medium">{m.full_name}</div><div className="text-xs text-muted">{m.email}</div></div>
                      {confirmRemove === m.id ? (
                        <span className="flex items-center gap-2 text-sm" role="group" aria-label={`Confirm remove ${m.full_name}`}>
                          Remove from {selected.name}?
                          <button type="button" autoFocus onClick={() => void onRemove(m.id)} disabled={busy} className="rounded-lg bg-bad px-3 py-1.5 font-medium text-bg">Yes, remove</button>
                          <button type="button" onClick={() => setConfirmRemove(null)} className="rounded-lg border border-line px-3 py-1.5">No</button>
                        </span>
                      ) : (
                        <button type="button" onClick={() => setConfirmRemove(m.id)} aria-label={`Remove ${m.full_name}`} className="rounded-lg border border-line px-3 py-1.5 text-sm hover:border-bad/60">Remove</button>
                      )}
                    </li>
                  ))}
                </ul>
              )}
              <div className="mt-5 flex flex-wrap items-end gap-3 border-t border-line pt-5">
                <div className="min-w-[14rem] flex-1">
                  <label htmlFor="g-add" className="mb-1 block text-sm font-medium">Add a person</label>
                  <select id="g-add" className={selectClass} value={toAdd} onChange={(e) => setToAdd(e.target.value)}>
                    <option value="">Choose...</option>
                    {candidates.map((u) => <option key={u.id} value={u.id}>{u.full_name} ({u.email})</option>)}
                  </select>
                </div>
                <button type="button" onClick={() => void onAdd()} disabled={!toAdd || busy} className="rounded-lg bg-accent px-5 py-3 font-medium text-bg hover:bg-accent2 disabled:opacity-50">Add</button>
              </div>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
