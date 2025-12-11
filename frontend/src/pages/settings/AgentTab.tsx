import { useEffect, useState } from 'react';
import { apiClient } from '@/api/client';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/use-toast';
import { AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';
import type { AgentConfig } from '@/types';

export default function AgentTab() {
  const [config, setConfig] = useState<AgentConfig>({
    persona: 'You are a helpful coding assistant.',
    allow_file_writes: true,
    allow_shell_commands: true,
    require_approval_for_large_plans: true,
    max_concurrent_tasks: 3,
    temperature: 0.7,
    max_tokens: 4096,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      setLoading(true);
      const data = await apiClient.getAgentConfig();
      setConfig(data);
    } catch (err) {
      console.error('Failed to load config:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);

    try {
      const result = await apiClient.updateAgentConfig(config);
      toast({
        title: 'Success',
        description: result.message,
      });
    } catch (err) {
      toast({
        title: 'Error',
        description: 'Failed to update agent configuration',
        variant: 'destructive',
      });
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Backend Integration Banner */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <div className="flex gap-3">
          <AlertCircle className="h-5 w-5 text-blue-600 dark:text-blue-500 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="text-sm font-medium text-blue-800 dark:text-blue-200">
              Backend Integration Required
            </h3>
            <p className="mt-1 text-sm text-blue-700 dark:text-blue-300">
              Agent configuration is currently saved to localStorage. Backend endpoint <code className="bg-blue-100 dark:bg-blue-800 px-1 rounded">/api/config/agent</code> needs to be implemented.
            </p>
          </div>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Persona */}
        <Card>
          <CardHeader>
            <CardTitle>Agent Persona</CardTitle>
            <CardDescription>
              Define the system prompt and personality for your coding agent
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="persona">System Prompt</Label>
              <Textarea
                id="persona"
                value={config.persona}
                onChange={(e) => setConfig({ ...config, persona: e.target.value })}
                className="min-h-[120px] font-mono text-sm"
                placeholder="You are a helpful coding assistant..."
                required
              />
              <p className="text-sm text-muted-foreground">
                This prompt defines how the agent behaves and responds
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Autonomy & Safety */}
        <Card>
          <CardHeader>
            <CardTitle>Autonomy & Safety</CardTitle>
            <CardDescription>
              Control what actions the agent can perform
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="allow_file_writes">Allow File Writes</Label>
                <p className="text-sm text-muted-foreground">
                  Agent can create, modify, and delete files
                </p>
              </div>
              <Switch
                id="allow_file_writes"
                checked={config.allow_file_writes}
                onCheckedChange={(checked) =>
                  setConfig({ ...config, allow_file_writes: checked })
                }
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="allow_shell_commands">Allow Shell Commands</Label>
                <p className="text-sm text-muted-foreground">
                  Agent can execute terminal commands
                </p>
              </div>
              <Switch
                id="allow_shell_commands"
                checked={config.allow_shell_commands}
                onCheckedChange={(checked) =>
                  setConfig({ ...config, allow_shell_commands: checked })
                }
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="require_approval">Require Approval for Large Plans</Label>
                <p className="text-sm text-muted-foreground">
                  Ask for confirmation before executing plans with many changes
                </p>
              </div>
              <Switch
                id="require_approval"
                checked={config.require_approval_for_large_plans}
                onCheckedChange={(checked) =>
                  setConfig({ ...config, require_approval_for_large_plans: checked })
                }
              />
            </div>
          </CardContent>
        </Card>

        {/* Defaults */}
        <Card>
          <CardHeader>
            <CardTitle>Default Settings</CardTitle>
            <CardDescription>
              Configure default behavior and limits
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="max_concurrent_tasks">Max Concurrent Tasks</Label>
              <Input
                id="max_concurrent_tasks"
                type="number"
                min="1"
                max="10"
                value={config.max_concurrent_tasks}
                onChange={(e) =>
                  setConfig({ ...config, max_concurrent_tasks: parseInt(e.target.value) })
                }
              />
              <p className="text-sm text-muted-foreground">
                Maximum number of tasks that can run simultaneously
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="temperature">Temperature</Label>
                <Input
                  id="temperature"
                  type="number"
                  step="0.1"
                  min="0"
                  max="2"
                  value={config.temperature || 0.7}
                  onChange={(e) =>
                    setConfig({ ...config, temperature: parseFloat(e.target.value) })
                  }
                />
                <p className="text-sm text-muted-foreground">0.0 - 2.0</p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="max_tokens">Max Tokens</Label>
                <Input
                  id="max_tokens"
                  type="number"
                  min="100"
                  max="200000"
                  value={config.max_tokens || 4096}
                  onChange={(e) =>
                    setConfig({ ...config, max_tokens: parseInt(e.target.value) })
                  }
                />
                <p className="text-sm text-muted-foreground">Max output length</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Actions */}
        <div className="flex items-center justify-end gap-3">
          <Button type="button" variant="outline" onClick={loadConfig} disabled={saving}>
            Reset
          </Button>
          <Button type="submit" disabled={saving}>
            {saving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <CheckCircle2 className="mr-2 h-4 w-4" />
                Save Configuration
              </>
            )}
          </Button>
        </div>
      </form>
    </div>
  );
}
