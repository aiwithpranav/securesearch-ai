// Change CONTACT_EMAIL to your own address. "Request demo" opens an email draft (no backend, no keys).
export const SITE_NAME = "SecureSearch AI";
export const CONTACT_EMAIL = "you@example.com";
export const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
export const DEMO_HREF = `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent("SecureSearch AI demo request")}`;
