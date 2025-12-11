// TypeScript types for the dashboard

export interface Project {
  id: string;
  tenant_id: string;
  name: string;                    // Project name (unique identifier)
  description?: string;            // Project description for LLM classification
  slack_channel_id?: string;       // Optional - for backwards compatibility
  repo_url: string;
  default_ref: string;
  created_at: string;
  updated_at: string;
}

export interface Run {
  id: string;
  project_id: string;
  tenant_id: string;
  status: 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled';
  task_prompt: string;
  slack_channel_id: string;
  cline_run_id?: string;
  cline_instance_address?: string;
  workspace_path?: string;
  created_at: string;
  started_at?: string;
  finished_at?: string;
  summary?: string;
}

export interface ApiKeyConfig {
  provider: string;
  api_key: string;
  model_id: string;
  base_url?: string;
}

export interface TestSlackRequest {
  channel_id: string;
  user_id?: string;
  user_name?: string;
  command?: string;
  text: string;
  team_id?: string;
  team_domain?: string;
}

export interface TestSlackResponse {
  success: boolean;
  message: string;
  run_id?: string;
  request_payload?: any;
  response_payload?: any;
}

export interface ProjectCreate {
  tenant_id?: string;
  slack_channel_id: string;
  repo_url: string;
  default_ref?: string;
}

export interface ProjectUpdate {
  repo_url?: string;
  default_ref?: string;
}

export interface RunFilters {
  status?: string;
  project_id?: string;
  limit?: number;
}
