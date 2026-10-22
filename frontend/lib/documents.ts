// Types, small helpers and API calls for the admin documents screens (Phase 3C).
//
// PRIVACY RULE (admin is not reader): nothing here, and no API answer, contains document TEXT.
// The screens show metadata, counts and status only.
import { ApiError, type Department } from "./api";
import { authedApi } from "./session";

export type JobStatus = "QUEUED" | "PROCESSING" | "READY" | "FAILED";

export type Job = {
  id: string;
  document_id: string;
  status: JobStatus;
  attempt: number;
  error_code: string | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
};

export type DocumentItem = {
  id: string;
  title: string;
  original_filename: string;
  document_type: string;
  department: Department;
  sensitivity_level: number;
  sensitivity_name: string;
  status: JobStatus;
  allowed_countries: string[] | null;
  current_version_no: number | null;
  version_count: number;
  chunk_count: number;
  latest_job: Job | null;
  uploaded_by: { id: string; full_name: string };
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
};

export type VersionUpload = { result: "CREATED" | "UNCHANGED"; version_no: number; document: DocumentItem };

export type DocumentPage = { items: DocumentItem[]; total: number; limit: number; offset: number };
export type Version = { id: string; version_no: number; content_hash: string; size_bytes: number; content_type: string; created_at: string };
export type NotificationItem = { id: string; kind: string; payload: Record<string, unknown>; read_at: string | null; created_at: string };

export const DOCUMENT_TYPES = ["POLICY", "RUNBOOK", "REPORT", "PLAYBOOK", "FORECAST", "CONTRACT", "OTHER"] as const;

// Blueprint 9.4: 0 PUBLIC ... 4 HIGHLY_RESTRICTED
export const SENSITIVITY_LEVELS = [
  { value: 0, name: "PUBLIC" },
  { value: 1, name: "INTERNAL" },
  { value: 2, name: "CONFIDENTIAL" },
  { value: 3, name: "RESTRICTED" },
  { value: 4, name: "HIGHLY_RESTRICTED" },
] as const;

export const STATUS_LABELS: Record<JobStatus, string> = {
  QUEUED: "Queued",
  PROCESSING: "Processing",
  READY: "Ready",
  FAILED: "Failed",
};

export const MAX_UPLOAD_BYTES = 50 * 1024 * 1024; // same limit as the server (NFR-03)
export const ALLOWED_EXTENSIONS = [".pdf", ".docx", ".txt", ".md"] as const;

export function fileExtension(name: string): string {
  const i = name.lastIndexOf(".");
  return i === -1 ? "" : name.slice(i).toLowerCase();
}

/** Quick checks in the browser. The server checks again and is the real gate. */
export function validateUploadFile(file: { name: string; size: number } | null): string | null {
  if (!file) return "Please choose a file.";
  if (!(ALLOWED_EXTENSIONS as readonly string[]).includes(fileExtension(file.name))) {
    return "This file type is not supported. Use PDF, DOCX, TXT or MD.";
  }
  if (file.size === 0) return "The file is empty.";
  if (file.size > MAX_UPLOAD_BYTES) return "The file is larger than 50 MB.";
  return null;
}

/** "in, us" -> ["IN","US"]. Empty text means no country limit. */
export function parseCountries(text: string): { codes: string[]; error: string | null } {
  const parts = text.split(",").map((p) => p.trim().toUpperCase()).filter(Boolean);
  if (parts.some((p) => !/^[A-Z]{2}$/.test(p))) {
    return { codes: [], error: "Use 2-letter country codes separated by commas, for example IN, US." };
  }
  return { codes: Array.from(new Set(parts)).sort(), error: null };
}

export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatDateTime(iso: string | null): string {
  if (!iso) return "-";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "-" : d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export const isBusy = (status: JobStatus): boolean => status === "QUEUED" || status === "PROCESSING";
export const anyBusy = (docs: DocumentItem[]): boolean =>
  docs.some((d) => isBusy(d.status) || (d.latest_job !== null && isBusy(d.latest_job.status)));

/** Turns an upload error into a plain-English message for the form. */
export function uploadErrorMessage(err: unknown): string {
  if (!(err instanceof ApiError)) return "Something went wrong. Please try again.";
  if (err.isNetworkError) return err.message;
  if (err.status === 409) return "A document with identical content already exists.";
  if (err.status === 429) return err.message;
  if (err.status === 413) return "The file is larger than 50 MB.";
  if (err.status === 401) return "Your session ended. Please sign in again.";
  if (err.status === 403) return "You do not have permission to upload documents.";
  if (err.status === 422) return err.message; // the server's message is already plain English
  return "Something went wrong. Please try again.";
}

/** What to tell the admin after a new version was sent. */
export function versionResultText(r: Pick<VersionUpload, "result" | "version_no">): string {
  return r.result === "UNCHANGED"
    ? `This file is the same as version ${r.version_no}. Nothing was changed.`
    : `Version ${r.version_no} was uploaded and is being processed. The current version stays in use until it is ready.`;
}

/** Errors of "upload a new version" and "restore": the server's own plain sentence is shown for a conflict. */
export function versionErrorMessage(err: unknown): string {
  if (err instanceof ApiError && err.status === 409) return err.message;
  if (err instanceof ApiError && err.status === 404) return "This document was not found.";
  return uploadErrorMessage(err);
}

// ----------------------------------------------------------------------------- API calls

export const uploadVersion = (id: string, form: FormData) =>
  authedApi<VersionUpload>(`/documents/${id}/versions`, { method: "POST", body: form });
export const restoreDocument = (id: string) => authedApi<DocumentItem>(`/documents/${id}/restore`, { method: "POST" });
export const listDocuments = (query: string) => authedApi<DocumentPage>(`/documents${query}`);
export const getDocument = (id: string) => authedApi<DocumentItem>(`/documents/${id}`);
export const listVersions = (id: string) => authedApi<Version[]>(`/documents/${id}/versions`);
export const listJobs = (documentId: string) =>
  authedApi<{ items: Job[]; total: number }>(`/ingestion/jobs?document_id=${documentId}&limit=20`);
export const reindexDocument = (id: string) => authedApi<Job>(`/documents/${id}/reindex`, { method: "POST" });
export const deleteDocument = (id: string) => authedApi<void>(`/documents/${id}`, { method: "DELETE" });
export const updateDocument = (id: string, body: Record<string, unknown>) =>
  authedApi<DocumentItem>(`/documents/${id}`, { method: "PATCH", body });
export const uploadDocument = (form: FormData) =>
  authedApi<DocumentItem>("/documents/upload", { method: "POST", body: form });
export const listDepartments = () => authedApi<Department[]>("/departments");
export const listNotifications = (unreadOnly: boolean) =>
  authedApi<NotificationItem[]>(`/notifications?limit=20${unreadOnly ? "&unread_only=true" : ""}`);
export const markNotificationRead = (id: string) =>
  authedApi<NotificationItem>(`/notifications/${id}/read`, { method: "POST" });

/** Plain-English reasons for the fixed error codes the server records on a failed job. */
export const FAILURE_REASONS: Record<string, string> = {
  UNSUPPORTED_TYPE: "The file type is not supported or the file is not what its name says.",
  EMPTY: "The file is empty.",
  NO_TEXT: "No readable text was found (scanned documents are not supported).",
  PARSE_ERROR: "The file could not be read. It may be damaged or protected.",
  TOO_LARGE: "The file is too large or has too much content.",
  STORAGE_ERROR: "The file store could not be reached.",
  EMBEDDING_ERROR: "The text could not be turned into vectors.",
  INTEGRITY_ERROR: "The stored file does not match its recorded fingerprint.",
  TIMEOUT: "Processing took too long and was stopped.",
  DELETED: "The document was deleted before processing finished.",
  INTERNAL: "An unexpected error occurred.",
};

export const failureReason = (code: string | null | undefined): string =>
  (code && FAILURE_REASONS[code]) || "The document could not be processed.";
