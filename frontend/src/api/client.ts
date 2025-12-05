import axios from 'axios';
import type {
  Project,
  ProjectCreate,
  ProjectUpdate,
  Run,
  RunFilters,
  ApiKeyConfig,
  TestSlackRequest,
  TestSlackResponse
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
  // RUN MONITORING
  // ============================================================================

  async getRuns(filters?: RunFilters): Promise<Run[]> {
    const params = new URLSearchParams();
    
    if (filters?.status) params.append('status', filters.status);
    if (filters?.project_id) params.append('project_id', filters.project_id);
    if (filters?.limit) params.append('limit', filters.limit.toString());

    const response = await api.get<Run[]>(`/api/runs?${params.toString()}`);
    return response.data;
  }

  async getRunDetails(id: string): Promise<Run> {
    const response = await api.get<Run>(`/api/runs/${id}`);
    return response.data;
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
