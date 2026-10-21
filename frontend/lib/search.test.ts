import { describe, expect, it } from "vitest";
import { ApiError } from "./api";
import { allWeak, MAX_QUERY, previewText, relevanceWord, scoreDetails, scorePercent, searchErrorText, validateQuery, whereText } from "./search";

describe("validateQuery", () => {
  it("refuses empty and whitespace-only questions", () => {
    expect(validateQuery("")).toContain("Type a question");
    expect(validateQuery("   \n ")).toContain("Type a question");
  });
  it("refuses a question that is too long and says by how much", () => {
    expect(validateQuery("x".repeat(MAX_QUERY + 1))).toContain(String(MAX_QUERY + 1));
  });
  it("accepts a normal question and one of exactly the maximum length", () => {
    expect(validateQuery("how many leave days?")).toBeNull();
    expect(validateQuery("x".repeat(MAX_QUERY))).toBeNull();
    expect(validateQuery("  padded  ")).toBeNull();
  });
});

describe("scorePercent and relevanceWord", () => {
  it("turns a 0 to 1 score into a whole percent and never leaves 0 to 100", () => {
    expect(scorePercent(0.824)).toBe(82);
    expect(scorePercent(-1)).toBe(0);
    expect(scorePercent(7)).toBe(100);
  });
  it("uses words as well as the bar, so colour is never the only signal", () => {
    expect(relevanceWord(0.95)).toBe("Strong match");
    expect(relevanceWord(0.4)).toBe("Possible match");
    expect(relevanceWord(0.01)).toBe("Weak match");
  });
});

describe("previewText", () => {
  it("keeps short passages whole", () => {
    expect(previewText("short text")).toEqual({ short: "short text", truncated: false });
  });
  it("cuts long passages at a word boundary and marks them", () => {
    const text = "word ".repeat(200);
    const { short, truncated } = previewText(text, 50);
    expect(truncated).toBe(true);
    expect(short.endsWith("…")).toBe(true);
    expect(short.length).toBeLessThanOrEqual(51);
    expect(short.replace("…", "").endsWith("wor")).toBe(false);
  });
});

describe("whereText", () => {
  it("joins what exists", () => {
    expect(whereText({ page_number: 3, section: "Alerts" })).toBe("Page 3 · Alerts");
    expect(whereText({ page_number: null, section: "Alerts" })).toBe("Alerts");
    expect(whereText({ page_number: 2, section: " " })).toBe("Page 2");
    expect(whereText({ page_number: null, section: null })).toBe("");
  });
});

describe("scoreDetails", () => {
  it("is empty for ordinary users", () => {
    expect(scoreDetails(null)).toEqual([]);
  });
  it("lists only the signals that exist, in a fixed order", () => {
    expect(scoreDetails({ rerank_score: 0.9123, keyword_rank: 2 })).toEqual([
      { label: "Keyword rank", value: "#2" },
      { label: "Reranker score", value: "0.912" },
    ]);
  });
});

describe("searchErrorText", () => {
  it("tells the person how long to wait when rate limited", () => {
    expect(searchErrorText(new ApiError(429, "Too many", "x", undefined, 12))).toBe("Too many searches. Try again in 12 seconds.");
    expect(searchErrorText(new ApiError(429, "Too many", "x", undefined, 1))).toBe("Too many searches. Try again in 1 second.");
    expect(searchErrorText(new ApiError(429, "Too many", "x"))).toBe("Too many searches. Try again shortly.");
  });
  it("has plain words for network and unknown errors and never shows raw details", () => {
    expect(searchErrorText(new ApiError(0, "Network error", "x"))).toContain("Can't reach the server");
    expect(searchErrorText(new ApiError(500, "Server", "stack trace here"))).not.toContain("stack trace");
    expect(searchErrorText(new Error("boom"))).toContain("could not be completed");
  });
});

describe("allWeak", () => {
  it("is true only when even the best passage is very weak", () => {
    expect(allWeak([{ score: 0.001 }, { score: 0.02 }])).toBe(true);
    expect(allWeak([{ score: 0.001 }, { score: 0.5 }])).toBe(false);
    expect(allWeak([])).toBe(false);
  });
});
