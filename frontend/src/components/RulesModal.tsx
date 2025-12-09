import { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import type { Project } from '../types';

interface RulesModalProps {
  project: Project;
  onClose: () => void;
  onSave: () => void;
}

export default function RulesModal({ project, onClose, onSave }: RulesModalProps) {
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadRules();
  }, [project.id]);

  const loadRules = async () => {
    try {
      setLoading(true);
      const data = await apiClient.getProjectRules(project.id);
      setContent(data.content || '');
    } catch (error) {
      console.error('Failed to load rules:', error);
      alert('Failed to load rules');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      await apiClient.updateProjectRules(project.id, content);
      onSave();
      onClose();
    } catch (error) {
      console.error('Failed to save rules:', error);
      alert('Failed to save rules');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm('Delete all agent rules? This will remove the .clinerules file.')) {
      return;
    }

    try {
      setSaving(true);
      await apiClient.deleteProjectRules(project.id);
      onSave();
      onClose();
    } catch (error) {
      console.error('Failed to delete rules:', error);
      alert('Failed to delete rules');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-11/12 max-w-4xl shadow-lg rounded-md bg-white">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-medium text-gray-900">
            Agent Rules - {project.repo_url}
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
          <>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={20}
              className="w-full px-3 py-2 text-gray-700 border rounded-lg focus:outline-none focus:border-blue-500 font-mono text-sm"
              placeholder="Enter Cline rules...&#10;&#10;Example:&#10;- Use TypeScript strict mode&#10;- Follow Airbnb style guide&#10;- Add JSDoc comments to all functions"
            />

            <div className="flex justify-between mt-4">
              <button
                onClick={handleDelete}
                disabled={saving}
                className="px-4 py-2 text-red-600 hover:text-red-900 disabled:opacity-50"
              >
                🗑️ Delete Rules
              </button>
              <div className="flex gap-2">
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
                  {saving ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
