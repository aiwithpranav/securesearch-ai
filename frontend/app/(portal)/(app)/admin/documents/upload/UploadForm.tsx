"use client";

import { DragEvent, FormEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ApiError, type Department } from "@/lib/api";
import {
  ALLOWED_EXTENSIONS,
  DOCUMENT_TYPES,
  formatBytes,
  listDepartments,
  parseCountries,
  SENSITIVITY_LEVELS,
  uploadDocument,
  uploadErrorMessage,
  validateUploadFile,
} from "@/lib/documents";
import { FieldError, FormErrorBox, Spinner } from "../../../../_auth/ui";
import { selectClass } from "../../_components/ui";

const inputClass = "w-full rounded-lg border bg-surface2 px-4 py-3 text-text placeholder:text-muted/60";

export function UploadForm() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [documentType, setDocumentType] = useState<string>("POLICY");
  const [sensitivity, setSensitivity] = useState("1");
  const [countries, setCountries] = useState("");
  const [departments, setDepartments] = useState<Department[]>([]);
  const [fileError, setFileError] = useState<string | null>(null);
  const [deptError, setDeptError] = useState<string | null>(null);
  const [countryError, setCountryError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [duplicateId, setDuplicateId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const deptRef = useRef<HTMLSelectElement>(null);
  const countryRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    listDepartments().then(setDepartments).catch(() => setFormError("The department list could not be loaded. Reload the page."));
  }, []);

  function choose(f: File | null) {
    setFile(f);
    setFileError(f ? validateUploadFile(f) : null);
    setFormError(null);
    setDuplicateId(null);
  }

  function onDrop(e: DragEvent<HTMLLabelElement>) {
    e.preventDefault();
    setDragging(false);
    choose(e.dataTransfer.files?.[0] ?? null);
  }

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (busy) return;
    const fErr = validateUploadFile(file);
    const dErr = departmentId === "" ? "Please choose a department." : null;
    const c = parseCountries(countries);
    setFileError(fErr);
    setDeptError(dErr);
    setCountryError(c.error);
    setFormError(null);
    setDuplicateId(null);
    if (fErr || dErr || c.error) {
      (fErr ? fileRef : dErr ? deptRef : countryRef).current?.focus();
      return;
    }

    const form = new FormData();
    form.append("file", file as File);
    form.append("department_id", departmentId);
    form.append("document_type", documentType);
    form.append("sensitivity_level", sensitivity);
    if (title.trim()) form.append("title", title.trim());
    if (c.codes.length) form.append("allowed_countries", c.codes.join(","));

    setBusy(true);
    try {
      const doc = await uploadDocument(form);
      router.push(`/admin/documents/${doc.id}`);
    } catch (err) {
      setBusy(false);
      setFormError(uploadErrorMessage(err));
      if (err instanceof ApiError && err.status === 409 && err.existingDocumentId) setDuplicateId(err.existingDocumentId);
    }
  }

  return (
    <main id="main" className="mx-auto w-full max-w-2xl px-5 py-12">
      <Link href="/admin/documents" className="text-sm text-muted hover:text-text">← Documents</Link>
      <h1 className="mt-4 text-3xl font-semibold tracking-tight">Upload document</h1>
      <p className="mt-2 text-muted">PDF, DOCX, TXT or MD, up to 50 MB. The file is checked, stored and then processed in the background.</p>

      <div role="alert" className="sr-only">{fileError ?? deptError ?? countryError ?? formError ?? ""}</div>
      {formError && (
        <div className="mt-6">
          <FormErrorBox message={formError} />
          {duplicateId && (
            <Link href={`/admin/documents/${duplicateId}`} className="mt-3 inline-block text-sm text-accent2 hover:underline">
              View the existing document
            </Link>
          )}
        </div>
      )}

      <form onSubmit={onSubmit} noValidate className="mt-8 space-y-6">
        <div>
          <label
            htmlFor="file"
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            className={`flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed p-8 text-center ${
              fileError ? "border-bad" : dragging ? "border-accent2 bg-surface" : "border-line"
            }`}
          >
            <span className="font-medium">{file ? file.name : "Choose a file or drop it here"}</span>
            <span className="mt-1 text-sm text-muted">
              {file ? formatBytes(file.size) : `Allowed: ${ALLOWED_EXTENSIONS.join(" ")}`}
            </span>
          </label>
          <input
            ref={fileRef}
            id="file"
            type="file"
            accept={ALLOWED_EXTENSIONS.join(",")}
            className="sr-only focus:not-sr-only focus:mt-2"
            aria-invalid={fileError ? true : undefined}
            aria-describedby={fileError ? "file-error" : undefined}
            onChange={(e) => choose(e.target.files?.[0] ?? null)}
          />
          {fileError && <FieldError id="file-error" message={fileError} />}
        </div>

        <div>
          <label htmlFor="title" className="mb-2 block text-sm font-medium">Title <span className="text-muted">(optional, defaults to the file name)</span></label>
          <input id="title" maxLength={200} className={`${inputClass} border-line`} value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>

        <div className="grid gap-6 sm:grid-cols-2">
          <div>
            <label htmlFor="department" className="mb-2 block text-sm font-medium">Department</label>
            <select ref={deptRef} id="department" className={`${selectClass} ${deptError ? "border-bad" : ""}`} value={departmentId}
              aria-invalid={deptError ? true : undefined} aria-describedby={deptError ? "dept-error" : undefined}
              onChange={(e) => { setDepartmentId(e.target.value); setDeptError(null); }}>
              <option value="">Choose...</option>
              {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
            {deptError && <FieldError id="dept-error" message={deptError} />}
          </div>
          <div>
            <label htmlFor="type" className="mb-2 block text-sm font-medium">Document type</label>
            <select id="type" className={selectClass} value={documentType} onChange={(e) => setDocumentType(e.target.value)}>
              {DOCUMENT_TYPES.map((t) => <option key={t} value={t}>{t.charAt(0) + t.slice(1).toLowerCase()}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="sensitivity" className="mb-2 block text-sm font-medium">Sensitivity</label>
            <select id="sensitivity" className={selectClass} value={sensitivity} onChange={(e) => setSensitivity(e.target.value)}>
              {SENSITIVITY_LEVELS.map((s) => <option key={s.value} value={s.value}>{s.value} · {s.name.replace("_", " ")}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="countries" className="mb-2 block text-sm font-medium">Allowed countries <span className="text-muted">(optional)</span></label>
            <input ref={countryRef} id="countries" placeholder="IN, US" className={`${inputClass} ${countryError ? "border-bad" : "border-line"}`}
              value={countries} aria-invalid={countryError ? true : undefined} aria-describedby={countryError ? "country-error" : "country-hint"}
              onChange={(e) => { setCountries(e.target.value); setCountryError(null); }} />
            {countryError ? <FieldError id="country-error" message={countryError} /> : <p id="country-hint" className="mt-2 text-sm text-muted">Leave empty for no country limit.</p>}
          </div>
        </div>

        <p className="text-sm text-muted">Who may read this document is set later (Phase 4). Until then nobody can read it.</p>

        <button type="submit" disabled={busy}
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-accent px-6 py-3 font-medium text-bg hover:bg-accent2 disabled:cursor-not-allowed disabled:opacity-70">
          {busy && <Spinner />}
          {busy ? "Uploading…" : "Upload"}
        </button>
      </form>
    </main>
  );
}
