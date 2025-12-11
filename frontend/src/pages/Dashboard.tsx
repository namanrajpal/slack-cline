import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ExternalLink, TrendingUp, DollarSign, Activity } from 'lucide-react';
import { SiGithub } from '@icons-pack/react-simple-icons';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { apiClient } from '../api/client';
import type { Project, Run } from '../types';

// Mock data generator
const generateMockData = (days: number, type: 'runs' | 'cost') => {
  const data = [];
  const now = new Date();
  for (let i = days - 1; i >= 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - i);
    const dateStr = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    
    if (type === 'runs') {
      data.push({
        date: dateStr,
        value: Math.floor(Math.random() * 15) + 5, // 5-20 runs per day
      });
    } else {
      data.push({
        date: dateStr,
        value: Number((Math.random() * 3 + 1).toFixed(2)), // $1-$4 per day
      });
    }
  }
  return data;
};

export default function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [recentRuns, setRecentRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Monitor card state
  const [metricType, setMetricType] = useState<'runs' | 'cost'>('runs');
  const [timeRange, setTimeRange] = useState<7 | 30 | 90>(7);
  const [selectedProject, setSelectedProject] = useState<string>('all');
  const [chartData, setChartData] = useState(generateMockData(7, 'runs'));

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    // Regenerate chart data when filters change
    setChartData(generateMockData(timeRange, metricType));
  }, [metricType, timeRange, selectedProject]);

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

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-foreground">Dashboard</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Overview of your Sline projects and runs
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
        <div className="bg-card overflow-hidden shadow-sm rounded-lg border border-border">
          <div className="px-4 py-5 sm:p-6">
            <dt className="text-sm font-medium text-muted-foreground truncate">
              Total Projects
            </dt>
            <dd className="mt-1 text-3xl font-semibold text-foreground">
              {projects.length}
            </dd>
          </div>
        </div>

        <div className="bg-card overflow-hidden shadow-sm rounded-lg border border-border">
          <div className="px-4 py-5 sm:p-6">
            <dt className="text-sm font-medium text-muted-foreground truncate">
              Active Runs
            </dt>
            <dd className="mt-1 text-3xl font-semibold text-primary">
              {activeRuns.length}
            </dd>
          </div>
        </div>

        <div className="bg-card overflow-hidden shadow-sm rounded-lg border border-border">
          <div className="px-4 py-5 sm:p-6">
            <dt className="text-sm font-medium text-muted-foreground truncate">
              Total Runs
            </dt>
            <dd className="mt-1 text-3xl font-semibold text-foreground">
              {recentRuns.length}
            </dd>
          </div>
        </div>
      </div>

      {/* Your Projects */}
      <div className="bg-card shadow-sm rounded-lg border border-border">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg font-medium text-foreground mb-4">
            Your Projects
          </h3>
          {projects.length === 0 ? (
            <div className="text-center py-6">
              <p className="text-muted-foreground mb-4">No projects configured yet</p>
              <Link
                to="/projects"
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-primary-foreground bg-primary hover:bg-primary/90"
              >
                Create Project
              </Link>
            </div>
          ) : (
            <div className="space-y-3">
              {projects.slice(0, 5).map((project) => (
                <a
                  key={project.id}
                  href={project.repo_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between p-3 bg-muted/50 rounded-md border border-border hover:border-primary/50 hover:bg-muted/70 transition-all group"
                >
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <SiGithub color="#181717" size={20} className="flex-shrink-0" />
                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-foreground group-hover:text-primary transition-colors">
                        {project.name}
                      </p>
                      <p className="text-sm text-muted-foreground truncate">{project.repo_url}</p>
                    </div>
                  </div>
                  <ExternalLink className="h-4 w-4 text-muted-foreground flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
                </a>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Monitor Card */}
      <div className="bg-card shadow-sm rounded-lg border border-border">
        <div className="px-4 py-5 sm:p-6">
          {/* Header with filters */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
            <h3 className="text-lg font-medium text-foreground">Monitor</h3>
            
            <div className="flex flex-wrap items-center gap-3">
              {/* Metric Toggle */}
              <div className="inline-flex rounded-lg border border-border bg-muted p-1">
                <button
                  onClick={() => setMetricType('runs')}
                  className={`inline-flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-all ${
                    metricType === 'runs'
                      ? 'bg-card text-foreground shadow-sm'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  <Activity className="h-4 w-4" />
                  Runs
                </button>
                <button
                  onClick={() => setMetricType('cost')}
                  className={`inline-flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-all ${
                    metricType === 'cost'
                      ? 'bg-card text-foreground shadow-sm'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  <DollarSign className="h-4 w-4" />
                  Cost
                </button>
              </div>

              {/* Time Range Selector */}
              <select
                value={timeRange}
                onChange={(e) => setTimeRange(Number(e.target.value) as 7 | 30 | 90)}
                className="rounded-md border border-border bg-card px-3 py-1.5 text-sm font-medium text-foreground shadow-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="7">7 days</option>
                <option value="30">30 days</option>
                <option value="90">90 days</option>
              </select>

              {/* Project Filter */}
              <select
                value={selectedProject}
                onChange={(e) => setSelectedProject(e.target.value)}
                className="rounded-md border border-border bg-card px-3 py-1.5 text-sm font-medium text-foreground shadow-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="all">All Projects</option>
                {projects.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-muted/30 rounded-lg p-4 border border-border/50">
              <p className="text-xs font-medium text-muted-foreground mb-1">Total</p>
              <p className="text-2xl font-bold text-foreground">
                {metricType === 'runs'
                  ? chartData.reduce((sum, d) => sum + d.value, 0)
                  : `$${chartData.reduce((sum, d) => sum + d.value, 0).toFixed(2)}`}
              </p>
            </div>
            <div className="bg-muted/30 rounded-lg p-4 border border-border/50">
              <p className="text-xs font-medium text-muted-foreground mb-1">Average</p>
              <p className="text-2xl font-bold text-foreground">
                {metricType === 'runs'
                  ? Math.round(chartData.reduce((sum, d) => sum + d.value, 0) / chartData.length)
                  : `$${(chartData.reduce((sum, d) => sum + d.value, 0) / chartData.length).toFixed(2)}`}
              </p>
            </div>
            <div className="bg-muted/30 rounded-lg p-4 border border-border/50">
              <div className="flex items-center gap-2 mb-1">
                <p className="text-xs font-medium text-muted-foreground">Trend</p>
                <TrendingUp className="h-3 w-3 text-green-500" />
              </div>
              <p className="text-2xl font-bold text-green-500">+12%</p>
            </div>
          </div>

          {/* Chart */}
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
                <XAxis
                  dataKey="date"
                  stroke="hsl(var(--muted-foreground))"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  stroke="hsl(var(--muted-foreground))"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(value) => (metricType === 'cost' ? `$${value}` : value)}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px',
                    color: 'hsl(var(--foreground))',
                  }}
                  formatter={(value: number) => [
                    metricType === 'cost' ? `$${value.toFixed(2)}` : value,
                    metricType === 'runs' ? 'Runs' : 'Cost',
                  ]}
                />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke="hsl(var(--primary))"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorValue)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-gradient-to-r from-primary to-primary/80 shadow-sm rounded-lg border border-border">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg font-medium text-primary-foreground mb-4">Quick Actions</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Link
              to="/projects"
              className="bg-primary-foreground/20 hover:bg-primary-foreground/30 text-primary-foreground rounded-md px-4 py-3 text-center font-medium transition border border-primary-foreground/20"
            >
              Manage Projects
            </Link>
            <Link
              to="/admin"
              className="bg-primary-foreground/20 hover:bg-primary-foreground/30 text-primary-foreground rounded-md px-4 py-3 text-center font-medium transition border border-primary-foreground/20"
            >
              Test Integration
            </Link>
            <Link
              to="/settings"
              className="bg-primary-foreground/20 hover:bg-primary-foreground/30 text-primary-foreground rounded-md px-4 py-3 text-center font-medium transition border border-primary-foreground/20"
            >
              Configure API Keys
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
