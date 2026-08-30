const STORAGE_PREFIX = "nexuswiki:active-ask-thread:";

function storageKey(workspaceId: string): string {
  return `${STORAGE_PREFIX}${workspaceId}`;
}

export function getActiveAskThread(workspaceId: string): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(storageKey(workspaceId));
}

export function setActiveAskThread(
  workspaceId: string,
  threadId: string,
): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(storageKey(workspaceId), threadId);
}

export function clearActiveAskThread(workspaceId: string): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(storageKey(workspaceId));
}
