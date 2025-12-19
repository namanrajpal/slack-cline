import { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import type { Project, ProjectCreate } from '../types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ChevronDown, ChevronRight, GitBranch, Trash2, FileText, Plus } from 'lucide-react';
import { SiGithub } from '@icons-pack/react-simple-icons';

export default function Projects() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [expandedProject, setExpandedProject] = useState<string | null>(null);
  const [formData, setFormData] = useState<ProjectCreate>({
    name: '',
    description: '',
    repo_url: '',
    default_ref: 'main'
  });

  // Per-project rules state (mock for now)
  const [projectRules, setProjectRules] = useState<Record<string, { type: string; content: string }>>({});

  useEffect(() => {
    loadProjects();
  }, []);

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
      await apiClient.createProject(formData);
      setShowForm(false);
      setFormData({ name: '', description: '', repo_url: '', default_ref: 'main' });
      loadProjects();
    } catch (err) {
      alert('Failed to create project');
      console.error(err);
    }
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

  const toggleProject = (projectId: string) => {
    setExpandedProject(expandedProject === projectId ? null : projectId);
  };

  const saveRules = (projectId: string, type: string, content: string) => {
    setProjectRules({
      ...projectRules,
      [projectId]: { type, content }
    });
    // TODO: Save to backend
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-muted-foreground">Loading projects...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-end items-center">
        <Dialog open={showForm} onOpenChange={setShowForm}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              New Project
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create New Project</DialogTitle>
              <DialogDescription>
                Add a repository for Sline to work with
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="project-name">Project Name</Label>
                <Input
                  id="project-name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="my-awesome-project"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description (Optional)</Label>
                <Textarea
                  id="description"
                  value={formData.description || ''}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Describe this project for LLM classification"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="repo-url">Repository URL</Label>
                <Input
                  id="repo-url"
                  value={formData.repo_url}
                  onChange={(e) => setFormData({ ...formData, repo_url: e.target.value })}
                  placeholder="https://github.com/org/repo.git"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="default-branch">Default Branch</Label>
                <Input
                  id="default-branch"
                  value={formData.default_ref}
                  onChange={(e) => setFormData({ ...formData, default_ref: e.target.value })}
                  placeholder="main"
                  required
                />
              </div>
              <div className="flex justify-end gap-3">
                <Button type="button" variant="outline" onClick={() => setShowForm(false)}>
                  Cancel
                </Button>
                <Button type="submit">
                  Create Project
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {error && (
        <div className="bg-destructive/10 border border-destructive/20 rounded-md p-4">
          <p className="text-destructive">{error}</p>
        </div>
      )}

      {/* Project Cards */}
      <div className="space-y-4">
        {projects.length === 0 ? (
          <Card>
            <CardContent className="text-center py-12">
              <SiGithub className="mx-auto mb-4 opacity-50 text-foreground" size={48} />
              <p className="text-muted-foreground mb-4">No projects yet</p>
              <Button onClick={() => setShowForm(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Create Your First Project
              </Button>
            </CardContent>
          </Card>
        ) : (
          projects.map((project) => {
            const isExpanded = expandedProject === project.id;
            const rules = projectRules[project.id] || { type: 'cline', content: '' };
            
            return (
              <Card key={project.id} className="overflow-hidden">
                {/* Collapsed Project Info */}
                <div
                  className="cursor-pointer hover:bg-muted/50 transition-colors"
                  onClick={() => toggleProject(project.id)}
                >
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3 flex-1">
                        <div className="text-muted-foreground">
                          {isExpanded ? (
                            <ChevronDown className="h-5 w-5" />
                          ) : (
                            <ChevronRight className="h-5 w-5" />
                          )}
                        </div>
                        <SiGithub className="text-foreground opacity-70 flex-shrink-0" size={20} />
                        <div className="flex-1 min-w-0">
                          <CardTitle className="text-base">{project.name}</CardTitle>
                          <CardDescription className="truncate">
                            {project.repo_url}
                          </CardDescription>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <GitBranch className="h-4 w-4" />
                          <span className="font-mono">{project.default_ref}</span>
                        </div>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDelete(project.id);
                          }}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                </div>

                {/* Expanded Rules & Workflows Section */}
                {isExpanded && (
                  <div className="border-t border-border">
                    <CardContent className="pt-6 space-y-4">
                      <div>
                        <h4 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                          <FileText className="h-4 w-4" />
                          Rules & Workflows
                        </h4>
                        <p className="text-xs text-muted-foreground mb-4">
                          Configure how Sline processes tasks for this project
                        </p>
                      </div>

                      <div className="space-y-3">
                        <div className="space-y-2">
                          <Label htmlFor={`rule-type-${project.id}`}>Rule Type</Label>
                          <Select
                            value={rules.type}
                            onValueChange={(value) =>
                              setProjectRules({
                                ...projectRules,
                                [project.id]: { ...rules, type: value }
                              })
                            }
                          >
                            <SelectTrigger id={`rule-type-${project.id}`}>
                              <SelectValue placeholder="Select rule type" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="cline">Cline Rules</SelectItem>
                              <SelectItem value="cursor">Cursor Rules</SelectItem>
                              <SelectItem value="claude_skills">Claude Skills</SelectItem>
                              <SelectItem value="agent_md">agent.md</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>

                        <div className="space-y-2">
                          <Label htmlFor={`rule-content-${project.id}`}>Rule Content</Label>
                          <Textarea
                            id={`rule-content-${project.id}`}
                            value={rules.content}
                            onChange={(e) =>
                              setProjectRules({
                                ...projectRules,
                                [project.id]: { ...rules, content: e.target.value }
                              })
                            }
                            className="min-h-[200px] font-mono text-sm"
                            placeholder="# Enter your rules here in YAML or JSON format..."
                          />
                        </div>

                        <div className="flex items-center justify-between pt-2">
                          {rules.content ? (
                            <Badge variant="secondary">
                              <FileText className="h-3 w-3 mr-1" />
                              Rules configured
                            </Badge>
                          ) : (
                            <Badge variant="outline">No rules configured</Badge>
                          )}
                          <Button
                            size="sm"
                            onClick={() => saveRules(project.id, rules.type, rules.content)}
                          >
                            Save Rules
                          </Button>
                        </div>

                        <div className="bg-muted/50 rounded-lg p-3 mt-4">
                          <p className="text-xs text-muted-foreground">
                            <strong className="text-foreground">Note:</strong> Backend integration for per-project rules coming soon. Rules will be saved to <code className="bg-background px-1 rounded">/api/projects/{'{projectId}'}/rules</code>
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </div>
                )}
              </Card>
            );
          })
        )}
      </div>
    </div>
  );
}
