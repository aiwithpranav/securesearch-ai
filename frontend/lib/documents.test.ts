import { describe, expect, it } from "vitest";
import { ApiError } from "./api";
import {
  anyBusy,
  fileExtension,
  formatBytes,
  isBusy,
  MAX_UPLOAD_BYTES,
  parseCountries,
  uploadErrorMessage,
  validateUploadFile,
  type DocumentItem,
} from "./documents";

describe("fileExtension", () => {
  it("uses the last extension in lower case", () => {
    expect(fileExtension("Report.PDF")).toBe(".pdf");
    expect(fileExtension("report.pdf.exe")).toBe(".exe");
    expect(fileExtension("noextension")).toBe("");
  });
});

describe("validateUploadFile", () => {
  it("asks for a file when none is chosen", () => {
    expect(validateUploadFile(null)).toBe("Please choose a file.");
  });
  it("accepts the four allowed types", () => {
    for (const n of ["a.pdf", "a.DOCX", "a.txt", "a.md"]) expect(validateUploadFile({ name: n, size: 10 })).toBeNull();
  });
  it("rejects other types, double extensions, empty and oversize files", () => {
    expect(validateUploadFile({ name: "virus.exe", size: 10 })).toContain("not supported");
    expect(validateUploadFile({ name: "report.pdf.exe", size: 10 })).toContain("not supported");
    expect(validateUploadFile({ name: "a.txt", size: 0 })).toBe("The file is empty.");
    expect(validateUploadFile({ name: "a.txt", size: MAX_UPLOAD_BYTES + 1 })).toBe("The file is larger than 50 MB.");
    expect(validateUploadFile({ name: "a.txt", size: MAX_UPLOAD_BYTES })).toBeNull();
  });
});

describe("parseCountries", () => {
  it("normalises codes", () => {
    expect(parseCountries(" in, US ,in")).toEqual({ codes: ["IN", "US"], error: null });
    expect(parseCountries("")).toEqual({ codes: [], error: null });
  });
  it("rejects anything that is not a 2-letter code", () => {
    expect(parseCountries("India").error).toContain("2-letter");
    expect(parseCountries("IN, U1").error).not.toBeNull();
  });
});

describe("formatBytes", () => {
  it("prints readable sizes", () => {
    expect(formatBytes(500)).toBe("500 B");
    expect(formatBytes(2048)).toBe("2.0 KB");
    expect(formatBytes(5 * 1024 * 1024)).toBe("5.0 MB");
  });
});

describe("busy detection", () => {
  const base = { latest_job: null } as unknown as DocumentItem;
  it("knows which statuses are unfinished", () => {
    expect(isBusy("QUEUED")).toBe(true);
    expect(isBusy("PROCESSING")).toBe(true);
    expect(isBusy("READY")).toBe(false);
    expect(isBusy("FAILED")).toBe(false);
  });
  it("keeps polling while a document or its latest job is unfinished", () => {
    expect(anyBusy([{ ...base, status: "READY" }])).toBe(false);
    expect(anyBusy([{ ...base, status: "QUEUED" }])).toBe(true);
    const reindexing = { ...base, status: "READY", latest_job: { status: "PROCESSING" } } as unknown as DocumentItem;
    expect(anyBusy([reindexing])).toBe(true);
  });
});

describe("uploadErrorMessage", () => {
  it("maps server answers to plain English", () => {
    expect(uploadErrorMessage(new ApiError(409, "Conflict", "x"))).toContain("identical content");
    expect(uploadErrorMessage(new ApiError(413, "t", "x"))).toBe("The file is larger than 50 MB.");
    expect(uploadErrorMessage(new ApiError(422, "t", "This file type is not supported."))).toBe("This file type is not supported.");
    expect(uploadErrorMessage(new ApiError(0, "Network error", "Can't reach the server."))).toBe("Can't reach the server.");
    expect(uploadErrorMessage(new ApiError(500, "t", "internal detail"))).not.toContain("internal");
    expect(uploadErrorMessage(new Error("boom"))).toBe("Something went wrong. Please try again.");
  });
});
