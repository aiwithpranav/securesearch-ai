// Public auth endpoints (no sign-in needed): forgot and reset password.
import { api } from "./api";

export async function forgotPassword(email: string): Promise<void> {
  await api<unknown>("/auth/forgot-password", { method: "POST", body: { email } });
}

export async function resetPassword(token: string, newPassword: string): Promise<void> {
  await api<void>("/auth/reset-password", { method: "POST", body: { token, new_password: newPassword } });
}
