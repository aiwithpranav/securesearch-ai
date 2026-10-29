"use client";

import { useEffect, useRef, useState } from "react";
import { listUsers, type UserItem } from "@/lib/access";
import { selectClass } from "./ui";

const SHOWN = 20;

/** Pick one person when there may be thousands: type to search (the server does the searching), then choose from
 *  the first matches. Replaces the old list of "the first 100 people". */
export function UserPicker({
  id, label, value, onChange, excludeIds = [], activeOnly = true,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (userId: string) => void;
  excludeIds?: string[];
  activeOnly?: boolean;
}) {
  const [text, setText] = useState("");
  const [results, setResults] = useState<UserItem[]>([]);
  const [total, setTotal] = useState(0);
  const [failed, setFailed] = useState(false);
  const latest = useRef(0); // only the newest request may change the list (answers can arrive out of order)
  const chosen = useRef(value);
  useEffect(() => {
    chosen.current = value;
  }, [value]);

  useEffect(() => {
    const n = ++latest.current;
    const timer = setTimeout(() => {
      listUsers({ q: text, limit: SHOWN, status: activeOnly ? "active" : "" })
        .then((page) => {
          if (n !== latest.current) return;
          setResults(page.items);
          setTotal(page.total);
          setFailed(false);
          if (chosen.current && !page.items.some((u) => u.id === chosen.current)) onChange(""); // the choice is no longer listed
        })
        .catch(() => {
          if (n === latest.current) setFailed(true);
        });
    }, text ? 250 : 0);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text, activeOnly]);

  const options = results.filter((u) => !excludeIds.includes(u.id));

  return (
    <div>
      <label htmlFor={`${id}-search`} className="mb-1 block text-sm font-medium">{label}</label>
      <input id={`${id}-search`} type="search" className={selectClass} value={text} maxLength={100} autoComplete="off"
        placeholder="Type a name or an email to search" onChange={(e) => setText(e.target.value)} />
      <select id={id} aria-label={`${label}: matching people`} className={`${selectClass} mt-2`} value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">Choose...</option>
        {options.map((u) => <option key={u.id} value={u.id}>{u.full_name} ({u.email})</option>)}
      </select>
      <p className="mt-1 text-xs text-muted" aria-live="polite">
        {failed ? "The people could not be loaded. Try again."
          : total > SHOWN ? `Showing the first ${SHOWN} of ${total} matches. Type to narrow the list.`
          : `${total} ${total === 1 ? "match" : "matches"}`}
      </p>
    </div>
  );
}
