import { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import type { Project } from '../types';

interface WorkflowsModalProps {
  project: Project;
  onClose: () => void;
  onSave: () => void;
}

export default function WorkflowsModal({ project, onClose, onSave }: WorkflowsModalProps) {
  const [workflows, setWorkflows] = useState<string[]>([]);
  const [selectedWorkflow, setSelectedWorkflow] = useState<string | null>(null);
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadWorkflows();
  }, [project.id]);

  const loadWorkflows = async () => {
    try {
      setLoading(true);
      const data = await apiClient.listWorkflows(project.id);
      setWorkflows(data.workflows);
    } catch (error) {
      console.error('Failed to load workflows:', error);
      alert('Failed to load workflows');
    } finally {
      setLoading(false);
    }
  };

  const loadWorkflow = async (name: string) => {
    try {
      const data = await apiClient.getWorkflow(project.id, name);
      setSelectedWorkflow(name);
      setContent(data.content);
    } catch (error) {
      console.error('Failed to load workflow:', error);
      alert('Failed to load workflow');
    }
  };

  const handleSave = async () => {
    if (!selectedWorkflow) return;

    try {
      setSaving(true);
      await apiClient.updateWorkflow(project.id, selectedWorkflow, content);
      alert('Workflow saved!');
    } catch (error) {
      console.error('Failed to save workflow:', error);
      alert('Failed to save workflow');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedWorkflow) return;
    if (!confirm(`Delete workflow "${selectedWorkflow}"?`)) return;

    try {
      setSaving(true);
      await apiClient.deleteWorkflow(project.id, selectedWorkflow);
      setWorkflows(workflows.filter(w => w !== selectedWorkflow));
      setSelectedWorkflow(null);
      setContent('');
      onSave();
    } catch (error) {
      console.error('Failed to delete workflow:', error);
      alert('Failed to delete workflow');
    } finally {
      setSaving(false);
    }
  };

  const handleNew = async () => {
    const name = prompt('Workflow name (e.g., "add-feature"):');
    if (!name) return;

    try {
      setSaving(true);
      await apiClient.createWorkflow(project.id, name, '# New Workflow\n\n');
      setWorkflows([...workflows, name].sort());
      loadWorkflow(name);
      onSave();
    } catch (error) {
      console.error('Failed to create workflow:', error);
      alert('Failed to create workflow');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-10 mx-auto p-5 border w-11/12 max-w-6xl shadow-lg rounded-md bg-white">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-medium text-gray-900">
            Agent Workflows - {project.repo_url}
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-500"
          >
            ✕
          </button>
        </div>

        {loading ? (
          <div className="text-center py-8">Loading...</div>
        ) : (
          <div className="flex gap-4" style={{ height: '500px' }}>
            {/* Left: Workflow List */}
            <div className="w-1/3 border-r pr-4 flex flex-col">
              <h4 className="font-medium mb-2">Workflows</h4>
              <div className="flex-1 overflow-y-auto border rounded-lg p-2 mb-2">
                {workflows.length === 0 ? (
                  <p className="text-gray-500 text-sm">No workflows yet</p>
                ) : (
                  <ul className="space-y-1">
                    {workflows.map(name => (
                      <li
                        key={name}
                        onClick={() => loadWorkflow(name)}
                        className={`px-3 py-2 rounded cursor-pointer hover:bg-gray-100 ${
                          selectedWorkflow === name ? 'bg-blue-100 font-medium' : ''
                        }`}
                      >
                        {name} {selectedWorkflow === name && '●'}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <button
                onClick={handleNew}
                disabled={saving}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
              >
                + New Workflow
              </button>
            </div>

            {/* Right: Editor */}
            <div className="w-2/3 flex flex-col">
              {selectedWorkflow ? (
                <>
                  <h4 className="font-medium mb-2">{selectedWorkflow}.md</h4>
                  <textarea
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    className="flex-1 w-full px-3 py-2 text-gray-700 border rounded-lg focus:outline-none focus:border-blue-500 font-mono text-sm"
                    placeholder="Enter workflow content..."
                  />
                  <div className="flex justify-end gap-2 mt-4">
                    <button
                      onClick={handleDelete}
                      disabled={saving}
                      className="px-4 py-2 text-red-600 hover:text-red-900 disabled:opacity-50"
                    >
                      🗑️ Delete
                    </button>
                    <button
                      onClick={onClose}
                      disabled={saving}
                      className="px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400 disabled:opacity-50"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSave}
                      disabled={saving}
                      className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                    >
                      {saving ? 'Saving...' : 'Save'}
                    </button>
                  </div>
                </>
              ) : (
                <div className="flex-1 flex items-center justify-center text-gray-500">
                  Select a workflow to edit or create a new one
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
