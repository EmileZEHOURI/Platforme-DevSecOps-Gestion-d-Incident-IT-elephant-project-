export interface CommentCreate {
  content: string;
}

export interface CommentResponse {
  id: number;
  incident_id: number;
  author_id: number;
  content: string;
  created_at: string;
  updated_at: string | null;
}
