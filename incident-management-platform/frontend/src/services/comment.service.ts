import { api } from "@/lib/api";
import type { CommentCreate, CommentResponse } from "@/types/comment";

export function createComment(incidentId: number, data: CommentCreate): Promise<CommentResponse> {
  return api<CommentResponse>(`/incidents/${encodeURIComponent(incidentId)}/comments`, {
    method: "POST",
    // The incident comes from the URL; identity and dates belong to the backend.
    body: JSON.stringify({ content: data.content.trim() }),
  });
}
