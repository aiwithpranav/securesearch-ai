// A question picked on Home (a suggestion or a recent question) is handed to the Ask screen through memory only.
// It is never put in a web address, storage or a log, and it never asks by itself: the person presses Ask.
let pending: string | null = null;

export function setPendingQuestion(q: string): void {
  pending = q;
}

/** Returns the waiting question once and forgets it. */
export function takePendingQuestion(): string | null {
  const q = pending;
  pending = null;
  return q;
}
