import { describe, expect, it } from "vitest";
import {
  MESSAGES,
  tokenFromHash,
  validateConfirm,
  validateCurrentPassword,
  validateEmail,
  validateNewPassword,
  validatePassword,
} from "./validation";

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
    expect(validateEmail("swara@demo")).toBeNull();
    expect(validateEmail("  swara@demo  ")).toBeNull();
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

describe("validateNewPassword", () => {
  it("follows the server rule: 12 to 128 characters", () => {
    expect(validateNewPassword("")).toBe(MESSAGES.newPasswordEmpty);
    expect(validateNewPassword("a".repeat(11))).toBe(MESSAGES.newPasswordShort);
    expect(validateNewPassword("a".repeat(12))).toBeNull();
    expect(validateNewPassword("a".repeat(128))).toBeNull();
    expect(validateNewPassword("a".repeat(129))).toBe(MESSAGES.newPasswordLong);
  });
});

describe("validateConfirm and validateCurrentPassword", () => {
  it("checks the two passwords match", () => {
    expect(validateConfirm("abc", "")).toBe(MESSAGES.confirmEmpty);
    expect(validateConfirm("abc", "abd")).toBe(MESSAGES.confirmMismatch);
    expect(validateConfirm("abc", "abc")).toBeNull();
  });
  it("needs the current password", () => {
    expect(validateCurrentPassword("")).toBe(MESSAGES.currentPasswordEmpty);
    expect(validateCurrentPassword("x")).toBeNull();
  });
});

describe("tokenFromHash", () => {
  it("reads the token from the reset link", () => {
    expect(tokenFromHash("#token=abc_DEF-123")).toBe("abc_DEF-123");
    expect(tokenFromHash("token=abc")).toBe("abc");
    expect(tokenFromHash("#a=1&token=xyz")).toBe("xyz");
  });
  it("returns null when there is no usable token", () => {
    expect(tokenFromHash("")).toBeNull();
    expect(tokenFromHash("#")).toBeNull();
    expect(tokenFromHash("#token=")).toBeNull();
    expect(tokenFromHash("#other=abc")).toBeNull();
  });
});
