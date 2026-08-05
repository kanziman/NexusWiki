export function workspacePath(workspaceId: string): string {
  if (workspaceId.trim().length === 0) {
    throw new TypeError("workspaceId must not be empty");
  }

  return `/w/${workspaceId}`;
}
