export interface User {
  id: string;
  email: string;
  created_at?: string;
  last_sign_in_at?: string;
}

export interface Case {
  id: string;
  title: string;
  description?: string;
  status: string;
  created_at: string;
  updated_at?: string;
}

export interface CaseCreate {
  title: string;
  description?: string;
}

export interface Document {
  id: string;
  filename: string;
  mimetype: string;
  size: number;
  status: string;
  case_id: string;
  created_at: string;
  updated_at?: string;
  error?: string;
}

export interface DocumentUpload {
  case_id: string;
  file: File;
}

export interface Report {
  id: string;
  title: string;
  template_id: string;
  status: string;
  case_id: string;
  created_at: string;
  updated_at?: string;
  content?: Record<string, string>;
  metadata?: Record<string, any>; // Added for layout type and other metadata
  error?: string;
}

export interface ReportCreate {
  title: string;
  template_id: string;
  case_id: string;
  layout_type: string; // Required, set default when creating report
}

export interface ReportSection {
  title: string;
  description: string;
}

export interface ReportTemplate {
  id: string;
  name: string;
  description: string;
  sections: Record<string, ReportSection>;
}

export interface Comment {
  id: string;
  report_id: string;
  section_id?: string;
  user_id: string;
  content: string;
  comment_type: string;
  status: string;
  is_internal: boolean;
  parent_id?: string;
  created_at: string;
  updated_at?: string;
  replies?: Comment[];
  user_name?: string;
  user_email?: string;
}

export interface CommentCreate {
  report_id: string;
  section_id?: string | null;
  content: string;
  comment_type: string;
  is_internal: boolean;
  parent_id?: string | null;
}

export interface CommentUpdate {
  content?: string;
  status?: string;
  comment_type?: string;
}
