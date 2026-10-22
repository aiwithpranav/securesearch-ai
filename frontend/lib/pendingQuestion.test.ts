import { describe, expect, it } from "vitest";
import { setPendingQuestion, takePendingQuestion } from "./pendingQuestion";

describe("pending question", () => {
  it("is empty when nothing was picked", () => expect(takePendingQuestion()).toBeNull());
  it("is handed over once and then forgotten", () => {
    setPendingQuestion("What is the leave policy?");
    expect(takePendingQuestion()).toBe("What is the leave policy?");
    expect(takePendingQuestion()).toBeNull();
  });
});
