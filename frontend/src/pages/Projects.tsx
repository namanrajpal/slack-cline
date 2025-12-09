import { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import type { Project, ProjectCreate } from '../types';
import RulesModal from '../components/RulesModal';
import WorkflowsModal from '../components/WorkflowsModal';

export default function Projects() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState<ProjectCreate>({
    slack_channel_id: '',
    repo_url: '',
    default_ref: 'main'
  });
  const [initialRules, setInitialRules] = useState<string>('');
  const [initialWorkflows, setInitialWorkflows] = useState<Array<{name: string, content: string}>>([]);
  const [showRulesSection, setShowRulesSection] = useState(false);
  const [showWorkflowsSection, setShowWorkflowsSection] = useState(false);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [showRulesModal, setShowRulesModal] = useState(false);
  const [showWorkflowsModal, setShowWorkflowsModal] = useState(false);
  const [githubToken, setGithubToken] = useState<string | null>(null);
  const [githubRepos, setGithubRepos] = useState<any[]>([]);
  const [loadingRepos, setLoadingRepos] = useState(false);

  useEffect(() => {
    loadProjects();
    
    // Load GitHub token from localStorage
    const token = localStorage.getItem('github_token');
    if (token) {
      setGithubToken(token);
    }

    // Listen for OAuth callback
    window.addEventListener('message', handleOAuthCallback);
    return () => window.removeEventListener('message', handleOAuthCallback);
  }, []);

  useEffect(() => {
    if (showForm && githubToken) {
      loadGitHubRepos();
    }
  }, [showForm, githubToken]);

  const handleOAuthCallback = (event: MessageEvent) => {
    if (event.data.type === 'github_auth_success') {
      const { token } = event.data;
      localStorage.setItem('github_token', token);
      setGithubToken(token);
    }
  };

  const loadGitHubRepos = async () => {
    if (!githubToken) return;
    
    try {
      setLoadingRepos(true);
      const data = await apiClient.getGitHubRepos(githubToken);
      
      if (data.connected && data.repos) {
        setGithubRepos(data.repos);
      }
    } catch (error) {
      console.error('Failed to load GitHub repos:', error);
    } finally {
      setLoadingRepos(false);
    }
  };

  const handleConnectGitHub = () => {
    const width = 600;
    const height = 700;
    const left = window.screen.width / 2 - width / 2;
    const top = window.screen.height / 2 - height / 2;
    
    window.open(
      'http://localhost:8000/auth/github/login?source=admin',
      'GitHub OAuth',
      `width=${width},height=${height},left=${left},top=${top}`
    );
  };

  const handleRepoSelect = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selectedRepo = githubRepos.find(r => r.clone_url === e.target.value);
    if (selectedRepo) {
      setFormData({
        ...formData,
        repo_url: selectedRepo.clone_url,
        default_ref: selectedRepo.default_branch
      });
    } else {
      setFormData({
        ...formData,
        repo_url: e.target.value
      });
    }
  };

  const loadProjects = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getProjects();
      setProjects(data);
    } catch (err) {
      setError('Failed to load projects');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const project = await apiClient.createProject(formData);
      
      // Save initial rules if provided
      if (initialRules.trim()) {
        await apiClient.updateProjectRules(project.id, initialRules);
      }
      
      // Save initial workflows if provided
      for (const workflow of initialWorkflows) {
        if (workflow.name.trim() && workflow.content.trim()) {
          await apiClient.createWorkflow(project.id, workflow.name, workflow.content);
        }
      }
      
      setShowForm(false);
      setFormData({ slack_channel_id: '', repo_url: '', default_ref: 'main' });
      setInitialRules('');
      setInitialWorkflows([]);
      setShowRulesSection(false);
      setShowWorkflowsSection(false);
      loadProjects();
    } catch (err) {
      alert('Failed to create project');
      console.error(err);
    }
  };

  const addWorkflow = () => {
    setInitialWorkflows([...initialWorkflows, { name: '', content: '' }]);
  };

  const updateWorkflow = (index: number, field: 'name' | 'content', value: string) => {
    const updated = [...initialWorkflows];
    updated[index][field] = value;
    setInitialWorkflows(updated);
  };

  const removeWorkflow = (index: number) => {
    setInitialWorkflows(initialWorkflows.filter((_, i) => i !== index));
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this project?')) return;
    
    try {
      await apiClient.deleteProject(id);
      loadProjects();
    } catch (err) {
      alert('Failed to delete project');
      console.error(err);
    }
  };

  if (loading) {
    return <div className="text-center py-8">Loading projects...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Projects</h2>
          <p className="mt-1 text-sm text-gray-500">
            Manage Slack channel to repository mappings
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          {showForm ? 'Cancel' : '+ New Project'}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {showForm && (
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Create New Project</h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Slack Channel ID
              </label>
              <input
                type="text"
                value={formData.slack_channel_id}
                onChange={(e) => setFormData({ ...formData, slack_channel_id: e.target.value })}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                placeholder="C1234567890"
                required
              />
            </div>
            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="block text-sm font-medium text-gray-700">
                  Repository
                </label>
                {!githubToken && (
                  <button
                    type="button"
                    onClick={handleConnectGitHub}
                    className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                  >
                    🔗 Connect GitHub
                  </button>
                )}
              </div>
              
              {githubToken && githubRepos.length > 0 ? (
                loadingRepos ? (
                  <div className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50 text-gray-500">
                    Loading repositories...
                  </div>
                ) : (
                  <select
                    value={formData.repo_url}
                    onChange={handleRepoSelect}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    required
                  >
                    <option value="">Select a repository...</option>
                    {githubRepos.map(repo => (
                      <option key={repo.full_name} value={repo.clone_url}>
                        {repo.full_name} {repo.private && '🔒'}
                      </option>
                    ))}
                  </select>
                )
              ) : (
                <input
                  type="text"
                  value={formData.repo_url}
                  onChange={(e) => setFormData({ ...formData, repo_url: e.target.value })}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  placeholder="https://github.com/org/repo.git"
                  required
                />
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Default Branch
              </label>
              <input
                type="text"
                value={formData.default_ref}
                onChange={(e) => setFormData({ ...formData, default_ref: e.target.value })}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                placeholder="main"
                required
              />
            </div>

            {/* Optional: Agent Rules */}
            <div className="border-t pt-4">
              <button
                type="button"
                onClick={() => setShowRulesSection(!showRulesSection)}
                className="flex items-center text-sm font-medium text-gray-700 hover:text-gray-900"
              >
                <span className="mr-2">{showRulesSection ? '▼' : '▶'}</span>
                Agent Rules (Optional)
              </button>
              {showRulesSection && (
                <div className="mt-2">
                  <textarea
                    value={initialRules}
                    onChange={(e) => setInitialRules(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 font-mono text-sm"
                    rows={6}
                    placeholder="Enter agent rules (one per line)...&#10;Example:&#10;- Use TypeScript strict mode&#10;- Add JSDoc comments&#10;- Follow company coding standards"
                  />
                </div>
              )}
            </div>

            {/* Optional: Workflows */}
            <div className="border-t pt-4">
              <button
                type="button"
                onClick={() => setShowWorkflowsSection(!showWorkflowsSection)}
                className="flex items-center text-sm font-medium text-gray-700 hover:text-gray-900"
              >
                <span className="mr-2">{showWorkflowsSection ? '▼' : '▶'}</span>
                Workflows (Optional)
              </button>
              {showWorkflowsSection && (
                <div className="mt-2 space-y-3">
                  {initialWorkflows.map((workflow, index) => (
                    <div key={index} className="border border-gray-200 rounded-md p-3">
                      <div className="flex justify-between items-center mb-2">
                        <input
                          type="text"
                          value={workflow.name}
                          onChange={(e) => updateWorkflow(index, 'name', e.target.value)}
                          className="flex-1 px-2 py-1 border border-gray-300 rounded text-sm"
                          placeholder="Workflow name (e.g., add-feature)"
                        />
                        <button
                          type="button"
                          onClick={() => removeWorkflow(index)}
                          className="ml-2 text-red-600 hover:text-red-800 text-sm"
                        >
                          🗑️ Remove
                        </button>
                      </div>
                      <textarea
                        value={workflow.content}
                        onChange={(e) => updateWorkflow(index, 'content', e.target.value)}
                        className="w-full px-2 py-1 border border-gray-300 rounded text-sm font-mono"
                        rows={4}
                        placeholder="Workflow content (markdown)..."
                      />
                    </div>
                  ))}
                  <button
                    type="button"
                    onClick={addWorkflow}
                    className="text-sm text-blue-600 hover:text-blue-800"
                  >
                    + Add Workflow
                  </button>
                </div>
              )}
            </div>

            <button
              type="submit"
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              Create Project
            </button>
          </form>
        </div>
      )}

      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Channel ID
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Repository
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Branch
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {projects.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-6 py-8 text-center text-gray-500">
                  No projects yet. Click "New Project" to create one.
                </td>
              </tr>
            ) : (
              projects.map((project) => (
                <tr key={project.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {project.slack_channel_id}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {project.repo_url}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {project.default_ref}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-2">
                    <button
                      onClick={() => {
                        setSelectedProject(project);
                        setShowRulesModal(true);
                      }}
                      className="text-blue-600 hover:text-blue-900"
                    >
                      📋 Rules
                    </button>
                    <button
                      onClick={() => {
                        setSelectedProject(project);
                        setShowWorkflowsModal(true);
                      }}
                      className="text-purple-600 hover:text-purple-900"
                    >
                      ⚙️ Workflows
                    </button>
                    <button
                      onClick={() => handleDelete(project.id)}
                      className="text-red-600 hover:text-red-900"
                    >
                      🗑️ Delete
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Modals */}
      {showRulesModal && selectedProject && (
        <RulesModal
          project={selectedProject}
          onClose={() => {
            setShowRulesModal(false);
            setSelectedProject(null);
          }}
          onSave={() => {
            loadProjects();
          }}
        />
      )}

      {showWorkflowsModal && selectedProject && (
        <WorkflowsModal
          project={selectedProject}
          onClose={() => {
            setShowWorkflowsModal(false);
            setSelectedProject(null);
          }}
          onSave={() => {
            loadProjects();
          }}
        />
      )}
    </div>
  );
}
