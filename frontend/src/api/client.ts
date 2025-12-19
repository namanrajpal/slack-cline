import axios from 'axios';
import type {
  Project,
  ProjectCreate,
  ProjectUpdate,
  Run,
  RunFilters,
  ApiKeyConfig,
  TestSlackRequest,
  TestSlackResponse,
  AgentConfig,
  RuleConfig,
  McpServer,
  McpServerCreate,
  ProviderConfig
} from '../types';

// Get API URL from environment variable or default to localhost
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// API client class
class ApiClient {
  // ============================================================================
  // PROJECT MANAGEMENT
  // ============================================================================

  async getProjects(): Promise<Project[]> {
    const response = await api.get<Project[]>('/api/projects');
    return response.data;
  }

  async createProject(data: ProjectCreate): Promise<Project> {
    const response = await api.post<Project>('/api/projects', data);
    return response.data;
  }

  async updateProject(id: string, data: ProjectUpdate): Promise<Project> {
    const response = await api.put<Project>(`/api/projects/${id}`, data);
    return response.data;
  }

  async deleteProject(id: string): Promise<void> {
    await api.delete(`/api/projects/${id}`);
  }

  // ============================================================================
  // CONFIGURATION
  // ============================================================================

  async getApiConfig(): Promise<ApiKeyConfig> {
    const response = await api.get<ApiKeyConfig>('/api/config/api-keys');
    return response.data;
  }

  async updateApiConfig(config: ApiKeyConfig): Promise<{ success: boolean; message: string; restart_required: boolean }> {
    const response = await api.post('/api/config/api-keys', config);
    return response.data;
  }

  // ============================================================================
  // TESTING/SIMULATION
  // ============================================================================

  async simulateSlackCommand(request: TestSlackRequest): Promise<TestSlackResponse> {
    const response = await api.post<TestSlackResponse>('/api/test/slack-command', request);
    return response.data;
  }

  // ============================================================================
  // AGENT CONFIGURATION
  // ============================================================================

  async getAgentConfig(): Promise<AgentConfig> {
    // TODO: Backend endpoint /api/config/agent
    // Temporary: return mock data
    return {
      persona: 'You are a helpful coding assistant.',
      allow_file_writes: true,
      allow_shell_commands: true,
      require_approval_for_large_plans: true,
      max_concurrent_tasks: 3,
      temperature: 0.7,
      max_tokens: 4096,
    };
  }

  async updateAgentConfig(config: AgentConfig): Promise<{ success: boolean; message: string }> {
    // TODO: Backend endpoint /api/config/agent
    // Temporary: save to localStorage
    localStorage.setItem('agent_config', JSON.stringify(config));
    return { success: true, message: 'Agent configuration saved (localStorage)' };
  }

  // ============================================================================
  // RULES & WORKFLOWS
  // ============================================================================

  async getRules(): Promise<RuleConfig[]> {
    // TODO: Backend endpoint /api/config/rules
    // Temporary: return mock data
    return [];
  }

  async createRule(rule: Omit<RuleConfig, 'id'>): Promise<RuleConfig> {
    // TODO: Backend endpoint /api/config/rules
    const newRule = { ...rule, id: Math.random().toString(36).substr(2, 9) };
    return newRule;
  }

  async updateRule(id: string, rule: Partial<RuleConfig>): Promise<RuleConfig> {
    // TODO: Backend endpoint /api/config/rules/:id
    return { id, ...rule } as RuleConfig;
  }

  async deleteRule(_id: string): Promise<void> {
    // TODO: Backend endpoint /api/config/rules/:id
  }

  async syncRuleFromRepo(_id: string): Promise<{ success: boolean; message: string }> {
    // TODO: Backend endpoint /api/config/rules/:id/sync
    return { success: false, message: 'Sync from repo feature coming soon' };
  }

  // ============================================================================
  // MCP SERVERS
  // ============================================================================

  async getMcpServers(): Promise<McpServer[]> {
    // TODO: Backend endpoint /api/mcp-servers
    // Temporary: return empty array
    return [];
  }

  async createMcpServer(server: McpServerCreate): Promise<McpServer> {
    // TODO: Backend endpoint /api/mcp-servers
    const newServer: McpServer = {
      id: Math.random().toString(36).substr(2, 9),
      name: server.name,
      type: server.type as 'filesystem' | 'git' | 'http' | 'database' | 'custom',
      endpoint: server.endpoint,
      auth_method: server.auth_method as 'none' | 'api_key' | 'oauth' | 'basic',
      auth_config: server.auth_config,
      status: 'disabled',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    return newServer;
  }

  async updateMcpServer(id: string, server: Partial<McpServerCreate>): Promise<McpServer> {
    // TODO: Backend endpoint /api/mcp-servers/:id
    return { id, ...server } as McpServer;
  }

  async deleteMcpServer(_id: string): Promise<void> {
    // TODO: Backend endpoint /api/mcp-servers/:id
  }

  async testMcpServer(_id: string): Promise<{ success: boolean; message: string; latency?: number }> {
    // TODO: Backend endpoint /api/mcp-servers/:id/test
    return { success: false, message: 'Backend integration required' };
  }

  // ============================================================================
  // ENHANCED PROVIDER CONFIG
  // ============================================================================

  async testProviderConnection(_config: ProviderConfig): Promise<{ success: boolean; message: string; model_info?: any }> {
    // TODO: Backend endpoint /api/config/api-keys/test
    return { success: false, message: 'Test connection feature coming soon' };
  }

  // ============================================================================
  // HEALTH CHECK
  // ============================================================================

  async healthCheck(): Promise<{ status: string; service: string }> {
    const response = await api.get('/health');
    return response.data;
  }
}

// Export singleton instance
export const apiClient = new ApiClient();
export default apiClient;
