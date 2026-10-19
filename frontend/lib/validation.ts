// Browser-side checks for the login form. The server checks again; this is only for fast feedback.
// Messages come from the blueprint (section 19.2). Keep the wording exact.
export const MESSAGES = {
  emailEmpty: "Please enter your email.",
  emailFormat: "Enter a valid email address, like name@company.com.",
  passwordEmpty: "Please enter your password.",
  wrongCredentials: "Email or password is incorrect.",
  network: "Can't reach the server. Check your connection and try again.",
  generic: "Something went wrong. Please try again.",
} as const;

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
