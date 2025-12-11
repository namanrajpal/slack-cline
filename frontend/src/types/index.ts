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

// Agent configuration types
export interface AgentConfig {
  persona: string; // System prompt / agent persona
  allow_file_writes: boolean;
  allow_shell_commands: boolean;
  require_approval_for_large_plans: boolean;
  default_project?: string;
  max_concurrent_tasks: number;
  temperature?: number;
  max_tokens?: number;
}

// Rules and workflows types
export interface RuleConfig {
  id: string;
  type: 'cline' | 'cursor' | 'claude_skills' | 'agent_md';
  name: string;
  source_type: 'file' | 'repo' | 'inline';
  source_location: string; // File path, repo URL, or inline content
  content?: string;
  last_synced_at?: string;
  enabled: boolean;
}

// MCP Server types
export interface McpServer {
  id: string;
  name: string;
  type: 'filesystem' | 'git' | 'http' | 'database' | 'custom';
  endpoint: string;
  status: 'connected' | 'error' | 'disabled';
  auth_method: 'none' | 'api_key' | 'oauth' | 'basic';
  auth_config?: Record<string, string>;
  created_at: string;
  updated_at: string;
}

export interface McpServerCreate {
  name: string;
  type: string;
  endpoint: string;
  auth_method: string;
  auth_config?: Record<string, string>;
}

// Enhanced provider config (extends existing ApiKeyConfig)
export interface ProviderConfig extends ApiKeyConfig {
  temperature?: number;
  max_tokens?: number;
  custom_headers?: Record<string, string>;
}
