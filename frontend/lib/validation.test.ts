import { describe, expect, it } from "vitest";
import { MESSAGES, validateEmail, validatePassword } from "./validation";

describe("validateEmail", () => {
  it("asks for an email when empty or only spaces", () => {
    expect(validateEmail("")).toBe(MESSAGES.emailEmpty);
    expect(validateEmail("   ")).toBe(MESSAGES.emailEmpty);
  });
  it("rejects values that are not shaped like an email", () => {
    for (const bad of ["abc", "a@", "@b", "a b@c", "a@b c"]) {
      expect(validateEmail(bad)).toBe(MESSAGES.emailFormat);
    }
  });
  it("accepts normal and demo emails", () => {
    expect(validateEmail("name@company.com")).toBeNull();
    expect(validateEmail("aisha@demo")).toBeNull();
    expect(validateEmail("  aisha@demo  ")).toBeNull();
  });
});

describe("validatePassword", () => {
  it("only requires something to be typed", () => {
    expect(validatePassword("")).toBe(MESSAGES.passwordEmpty);
    expect(validatePassword("x")).toBeNull();
  });
});

describe("messages", () => {
  it("keep the exact wording from the blueprint", () => {
    expect(MESSAGES.wrongCredentials).toBe("Email or password is incorrect.");
    expect(MESSAGES.network).toBe("Can't reach the server. Check your connection and try again.");
  });
});
