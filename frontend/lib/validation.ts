// Browser-side checks for the auth forms. The server checks again; this is only for fast feedback.
// Login messages come from the blueprint (section 19.2). Keep the wording exact.
export const MESSAGES = {
  emailEmpty: "Please enter your email.",
  emailFormat: "Enter a valid email address, like name@company.com.",
  passwordEmpty: "Please enter your password.",
  wrongCredentials: "Email or password is incorrect.",
  network: "Can't reach the server. Check your connection and try again.",
  generic: "Something went wrong. Please try again.",
  currentPasswordEmpty: "Please enter your current password.",
  newPasswordEmpty: "Please enter a new password.",
  newPasswordShort: "Use at least 12 characters.",
  newPasswordLong: "Use 128 characters or fewer.",
  confirmEmpty: "Please repeat the new password.",
  confirmMismatch: "The two passwords do not match.",
  resetLinkInvalid: "This link is invalid or has expired.",
} as const;

export const MIN_PASSWORD_LENGTH = 12; // same rule as the server (ADR 023)
export const MAX_PASSWORD_LENGTH = 128;

// "something@something" is enough. Demo accounts look like aisha@demo (no ".com").
const EMAIL_SHAPE = /^[^@\s]+@[^@\s]+$/;

export function validateEmail(value: string): string | null {
  const v = value.trim();
  if (v === "") return MESSAGES.emailEmpty;
  if (!EMAIL_SHAPE.test(v)) return MESSAGES.emailFormat;
  return null;
}

export function validatePassword(value: string): string | null {
  return value === "" ? MESSAGES.passwordEmpty : null;
}

export function validateCurrentPassword(value: string): string | null {
  return value === "" ? MESSAGES.currentPasswordEmpty : null;
}

export function validateNewPassword(value: string): string | null {
  if (value === "") return MESSAGES.newPasswordEmpty;
  if (value.length < MIN_PASSWORD_LENGTH) return MESSAGES.newPasswordShort;
  if (value.length > MAX_PASSWORD_LENGTH) return MESSAGES.newPasswordLong;
  return null;
}

export function validateConfirm(newPassword: string, confirm: string): string | null {
  if (confirm === "") return MESSAGES.confirmEmpty;
  if (confirm !== newPassword) return MESSAGES.confirmMismatch;
  return null;
}

/** Reads "#token=..." from a URL hash. Returns null when there is no token. */
export function tokenFromHash(hash: string): string | null {
  const m = /^#?(?:.*&)?token=([A-Za-z0-9_-]+)/.exec(hash);
  return m ? m[1] : null;
}

/** Notices shown on the login page after another flow ("?notice=password-changed"). */
export const NOTICES: Record<string, string> = {
  "password-changed": "Your password was changed. Sign in again with your new password.",
  "password-reset": "Your password was updated. Sign in with your new password.",
  "signed-out-everywhere": "You were signed out on all devices.",
};
