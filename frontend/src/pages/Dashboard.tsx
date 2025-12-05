import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import type { Project, Run } from '../types';
import { getStatusIcon, formatRelativeTime } from '../utils/formatters';

export default function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [recentRuns, setRecentRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [projectsData, runsData] = await Promise.all([
        apiClient.getProjects(),
        apiClient.getRuns({ limit: 10 }),
      ]);
      
      setProjects(projectsData);
      setRecentRuns(runsData);
    } catch (err) {
      setError('Failed to load dashboard data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-gray-500">Loading dashboard...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4">
        <p className="text-red-800">{error}</p>
        <button
          onClick={loadData}
          className="mt-2 text-red-600 hover:text-red-800 underline"
        >
          Try again
        </button>
      </div>
    );
  }

  const activeRuns = recentRuns.filter(r => r.status === 'running' || r.status === 'queued');
  const completedRuns = recentRuns.filter(r => r.status === 'succeeded' || r.status === 'failed' || r.status === 'cancelled');

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Dashboard</h2>
        <p className="mt-1 text-sm text-gray-500">
          Overview of your Slack-Cline projects and runs
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <dt className="text-sm font-medium text-gray-500 truncate">
              Total Projects
            </dt>
            <dd className="mt-1 text-3xl font-semibold text-gray-900">
              {projects.length}
            </dd>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <dt className="text-sm font-medium text-gray-500 truncate">
              Active Runs
            </dt>
            <dd className="mt-1 text-3xl font-semibold text-blue-600">
              {activeRuns.length}
            </dd>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <dt className="text-sm font-medium text-gray-500 truncate">
              Total Runs
            </dt>
            <dd className="mt-1 text-3xl font-semibold text-gray-900">
              {recentRuns.length}
            </dd>
          </div>
        </div>
      </div>

      {/* Recent Projects */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">
            Recent Projects
          </h3>
          {projects.length === 0 ? (
            <div className="text-center py-6">
              <p className="text-gray-500 mb-4">No projects configured yet</p>
              <Link
                to="/projects"
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700"
              >
                Create Project
              </Link>
            </div>
          ) : (
            <div className="space-y-3">
              {projects.slice(0, 5).map((project) => (
                <div
                  key={project.id}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-md"
                >
                  <div>
                    <p className="font-medium text-gray-900">
                      Channel: {project.slack_channel_id}
                    </p>
                    <p className="text-sm text-gray-500">{project.repo_url}</p>
                  </div>
                  <Link
                    to="/projects"
                    className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                  >
                    View →
                  </Link>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Recent Runs */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">
            Recent Runs
          </h3>
          {recentRuns.length === 0 ? (
            <div className="text-center py-6">
              <p className="text-gray-500 mb-4">No runs yet</p>
              <Link
                to="/admin"
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700"
              >
                Test Integration
              </Link>
            </div>
          ) : (
            <div className="space-y-3">
              {recentRuns.map((run) => (
                <div
                  key={run.id}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-md"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xl">{getStatusIcon(run.status)}</span>
                      <p className="font-medium text-gray-900">
                        {run.task_prompt.substring(0, 60)}
                        {run.task_prompt.length > 60 ? '...' : ''}
                      </p>
                    </div>
                    <p className="text-sm text-gray-500 mt-1">
                      {formatRelativeTime(run.created_at)} • Status: {run.status}
                    </p>
                  </div>
                  <Link
                    to="/runs"
                    className="text-blue-600 hover:text-blue-800 text-sm font-medium ml-4"
                  >
                    Details →
                  </Link>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-gradient-to-r from-blue-500 to-blue-600 shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg font-medium text-white mb-4">Quick Actions</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Link
              to="/projects"
              className="bg-white bg-opacity-20 hover:bg-opacity-30 text-white rounded-md px-4 py-3 text-center font-medium transition"
            >
              Manage Projects
            </Link>
            <Link
              to="/admin"
              className="bg-white bg-opacity-20 hover:bg-opacity-30 text-white rounded-md px-4 py-3 text-center font-medium transition"
            >
              Test Integration
            </Link>
            <Link
              to="/settings"
              className="bg-white bg-opacity-20 hover:bg-opacity-30 text-white rounded-md px-4 py-3 text-center font-medium transition"
            >
              Configure API Keys
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
