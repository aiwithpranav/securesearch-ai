// "Has this person seen the welcome tour?" is remembered in this browser only (localStorage),
// per user id. The server has no such field (the API contract is frozen), so on a new
// browser or device the tour shows once more. That is a known, accepted limitation.
// Every storage call is wrapped: private windows or blocked storage must never break the page.
const key = (userId: string) => `securesearch.tour.v1.${userId}`;
export const OPEN_TOUR_EVENT = "securesearch:open-tour";

export function hasSeenTour(userId: string): boolean {
  try {
    return window.localStorage.getItem(key(userId)) === "seen";
  } catch {
    return true; // if we cannot remember, do not nag
  }
}

export function markTourSeen(userId: string): void {
  try {
    window.localStorage.setItem(key(userId), "seen");
  } catch {
    // ignore
  }
}
