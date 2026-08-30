import { apiFetch } from "@/lib/api-client";

export type AskThreadSummary = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type StoredCitations = {
  text: string;
  resolved: { alias: string; kind: string; id: string }[];
};

export type AskThreadMessage = {
  id: string;
  client_turn_id: string;
  question: string;
  answer_text: string;
  citations: StoredCitations;
  status: "streaming" | "resolved" | "no-evidence" | "error";
  created_at: string;
};

export type AskThreadDetail = AskThreadSummary & {
  messages: AskThreadMessage[];
};

export function listAskThreads(workspaceId: string) {
  return apiFetch<AskThreadSummary[]>(`/workspaces/${workspaceId}/ask/threads`);
}

export function getAskThread(workspaceId: string, threadId: string) {
  return apiFetch<AskThreadDetail>(
    `/workspaces/${workspaceId}/ask/threads/${threadId}`,
  );
}

export function renameAskThread(
  workspaceId: string,
  threadId: string,
  title: string,
) {
  return apiFetch<AskThreadSummary>(
    `/workspaces/${workspaceId}/ask/threads/${threadId}`,
    { method: "PATCH", body: { title } },
  );
}

export function deleteAskThread(workspaceId: string, threadId: string) {
  return apiFetch<AskThreadSummary>(
    `/workspaces/${workspaceId}/ask/threads/${threadId}`,
    { method: "DELETE" },
  );
}
