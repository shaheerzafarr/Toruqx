/**
 * Strict TypeScript interfaces mirroring our JSON API responses and PostgreSQL/SQLAlchemy schemas.
 */

export interface User {
  id: string; // UUID v4 format
  username: string;
  created_at: string; // ISO 8601 UTC timestamp
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface ChatSession {
  id: string; // UUID v4 format
  title: string;
  created_at: string; // ISO 8601 UTC timestamp
  user_id?: string | null;
}

export interface CitationSource {
  filename: string;
  chunk_index: number;
  score: number;
  text: string;
}

export interface Message {
  id: string; // UUID v4 format
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string; // ISO 8601 UTC timestamp
  sources?: CitationSource[];
}

export type UploadStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface DocumentUploadStatus {
  id: string; // UUID v4 format
  filename: string;
  file_size: number; // in bytes
  chunk_count: number;
  status: UploadStatus;
  error_message?: string | null;
  created_at: string; // ISO 8601 UTC timestamp
}

export interface APIErrorResponse {
  detail: string | Array<{ loc: string[]; msg: string; type: string }>;
  status: 'error';
}
