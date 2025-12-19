import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ExternalLink, TrendingUp, DollarSign, Activity, Star, GitFork, Circle, MessageSquare, ArrowRight } from 'lucide-react';
import { SiGithub } from '@icons-pack/react-simple-icons';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { apiClient } from '../api/client';
import type { Project } from '../types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface GitHubRepoStats {
  stargazers_count: number;
  forks_count: number;
  language: string | null;
  updated_at: string;
}

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
  // const [recentRuns, setRecentRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [githubStats, setGithubStats] = useState<Map<string, GitHubRepoStats>>(new Map());
  
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
      
      const projectsData = await apiClient.getProjects();
      
      setProjects(projectsData);

      // Fetch GitHub stats for each project
      const statsMap = new Map<string, GitHubRepoStats>();
      for (const project of projectsData) {
        try {
          const stats = await fetchGitHubStats(project.repo_url);
          if (stats) {
            statsMap.set(project.id, stats);
          }
        } catch (err) {
          console.error(`Failed to fetch GitHub stats for ${project.repo_url}`, err);
        }
      }
      setGithubStats(statsMap);
    } catch (err) {
      setError('Failed to load dashboard data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchGitHubStats = async (repoUrl: string): Promise<GitHubRepoStats | null> => {
    try {
      // Extract owner and repo from GitHub URL
      const match = repoUrl.match(/github\.com[:/]([^/]+)\/([^/.]+)/);
      if (!match) return null;
      
      const [, owner, repo] = match;
      const response = await fetch(`https://api.github.com/repos/${owner}/${repo}`);
      
      if (!response.ok) return null;
      
      const data = await response.json();
      return {
        stargazers_count: data.stargazers_count || 0,
        forks_count: data.forks_count || 0,
        language: data.language || null,
        updated_at: data.updated_at || new Date().toISOString(),
      };
    } catch (err) {
      console.error('Error fetching GitHub stats:', err);
      return null;
    }
  };

  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);
    
    if (diffInSeconds < 60) return 'just now';
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
    if (diffInSeconds < 2592000) return `${Math.floor(diffInSeconds / 86400)}d ago`;
    return `${Math.floor(diffInSeconds / 2592000)}mo ago`;
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


  return (
    <div className="space-y-6">
      {/* Chat CTA Card */}
      <Card className="bg-gradient-to-br from-primary/5 via-primary/10 to-primary/5 border-primary/20">
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                <MessageSquare className="h-6 w-6 text-primary" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-foreground">Chat with Sline</h3>
                <p className="text-sm text-muted-foreground">
                  Ask questions about your codebase, get help debugging, or refactor code
                </p>
              </div>
            </div>
            <Link to="/chat">
              <Button className="gap-2">
                Start Chat
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>

      {/* Your Projects */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-foreground">
            Your Projects
          </h3>
          <Link
            to="/projects"
            className="text-sm text-primary hover:text-primary/80 font-medium"
          >
            View all →
          </Link>
        </div>
        
        {projects.length === 0 ? (
          <Card>
            <CardContent className="text-center py-12">
              <SiGithub className="mx-auto mb-4 opacity-50 text-foreground" size={48} />
              <p className="text-muted-foreground mb-4">No projects configured yet</p>
              <Link
                to="/projects"
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-primary-foreground bg-primary hover:bg-primary/90"
              >
                Create Project
              </Link>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.slice(0, 6).map((project) => {
              const stats = githubStats.get(project.id);
              return (
                <Card
                  key={project.id}
                  className="hover:shadow-lg hover:border-primary/50 transition-all group cursor-pointer"
                >
                  <a
                    href={project.repo_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block"
                  >
                    <CardHeader className="pb-3">
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2">
                          <SiGithub className="flex-shrink-0 text-foreground opacity-70" size={20} />
                          <CardTitle className="text-base font-semibold group-hover:text-primary transition-colors">
                            {project.name}
                          </CardTitle>
                        </div>
                        <ExternalLink className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                      </div>
                      {project.description && (
                        <CardDescription className="line-clamp-2">
                          {project.description}
                        </CardDescription>
                      )}
                    </CardHeader>
                    <CardContent className="pt-0">
                      <div className="flex items-center gap-4 text-sm text-muted-foreground">
                        {stats && (
                          <>
                            <div className="flex items-center gap-1">
                              <Star className="h-3.5 w-3.5" />
                              <span>{stats.stargazers_count}</span>
                            </div>
                            <div className="flex items-center gap-1">
                              <GitFork className="h-3.5 w-3.5" />
                              <span>{stats.forks_count}</span>
                            </div>
                            {stats.language && (
                              <div className="flex items-center gap-1">
                                <Circle className="h-2 w-2 fill-current" />
                                <span>{stats.language}</span>
                              </div>
                            )}
                          </>
                        )}
                      </div>
                      {stats && (
                        <div className="mt-2 text-xs text-muted-foreground">
                          Updated {formatTimeAgo(stats.updated_at)}
                        </div>
                      )}
                    </CardContent>
                  </a>
                </Card>
              );
            })}
          </div>
        )}
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
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Link
              to="/projects"
              className="bg-primary-foreground/20 hover:bg-primary-foreground/30 text-primary-foreground rounded-md px-4 py-3 text-center font-medium transition border border-primary-foreground/20"
            >
              Manage Projects
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
