import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { AlertCircle, FileText, RefreshCw, Pencil } from 'lucide-react';

export default function RulesTab() {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingRule, setEditingRule] = useState({
    type: 'cline' as 'cline' | 'cursor' | 'claude_skills' | 'agent_md',
    name: '',
    content: '',
  });

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
              Rules & workflows management needs backend endpoint <code className="bg-blue-100 dark:bg-blue-800 px-1 rounded">/api/config/rules</code> to be implemented.
            </p>
          </div>
        </div>
      </div>

      {/* Cline Rules */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Cline Rules & Workflows</CardTitle>
              <CardDescription>
                Configure how Cline processes tasks and makes decisions
              </CardDescription>
            </div>
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
              <DialogTrigger asChild>
                <Button
                  onClick={() => {
                    setEditingRule({ type: 'cline', name: 'Cline Rules', content: '' });
                  }}
                >
                  <Pencil className="mr-2 h-4 w-4" />
                  Edit Rules
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle>Edit {editingRule.type === 'cline' ? 'Cline' : editingRule.type === 'cursor' ? 'Cursor' : 'Claude'} Rules</DialogTitle>
                  <DialogDescription>
                    Define rules and workflows in YAML or JSON format
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="rule-name">Rule Name</Label>
                    <Input
                      id="rule-name"
                      value={editingRule.name}
                      onChange={(e) =>
                        setEditingRule({ ...editingRule, name: e.target.value })
                      }
                      placeholder="e.g., Default Workflow"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="rule-content">Rule Content</Label>
                    <Textarea
                      id="rule-content"
                      value={editingRule.content}
                      onChange={(e) =>
                        setEditingRule({ ...editingRule, content: e.target.value })
                      }
                      className="min-h-[300px] font-mono text-sm"
                      placeholder="# Enter your rules here in YAML or JSON format..."
                    />
                  </div>
                  <div className="flex justify-end gap-3">
                    <Button variant="outline" onClick={() => setDialogOpen(false)}>
                      Cancel
                    </Button>
                    <Button onClick={() => setDialogOpen(false)}>
                      Save Rules
                    </Button>
                  </div>
                </div>
              </DialogContent>
            </Dialog>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg border border-border">
            <div className="flex items-center gap-3">
              <FileText className="h-5 w-5 text-muted-foreground" />
              <div>
                <p className="font-medium text-sm">No rules configured</p>
                <p className="text-xs text-muted-foreground">Click "Edit Rules" to get started</p>
              </div>
            </div>
            <Badge variant="outline">Not configured</Badge>
          </div>
        </CardContent>
      </Card>

      {/* Cursor / Agent.md / Claude Skills */}
      <Card>
        <CardHeader>
          <CardTitle>Other Rule Formats</CardTitle>
          <CardDescription>
            Support for Cursor rules, Claude skills, and agent.md configurations
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="rule-type">Rule Type</Label>
            <Select defaultValue="cursor">
              <SelectTrigger id="rule-type">
                <SelectValue placeholder="Select rule type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="cursor">Cursor Rules</SelectItem>
                <SelectItem value="claude_skills">Claude Skills</SelectItem>
                <SelectItem value="agent_md">agent.md</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg border border-border">
            <div className="flex items-center gap-3">
              <FileText className="h-5 w-5 text-muted-foreground" />
              <div>
                <p className="font-medium text-sm">No rules configured</p>
                <p className="text-xs text-muted-foreground">Configure rules for enhanced agent behavior</p>
              </div>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled>
                <RefreshCw className="mr-2 h-3 w-3" />
                Sync from Repo
              </Button>
              <Button size="sm" disabled>
                Edit
              </Button>
            </div>
          </div>

          <p className="text-sm text-muted-foreground">
            <strong>Note:</strong> Sync from repository feature coming soon. You'll be able to automatically pull rules from your Git repos.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
