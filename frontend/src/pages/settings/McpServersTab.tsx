import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { AlertCircle, Plus, Server } from 'lucide-react';

export default function McpServersTab() {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [newServer, setNewServer] = useState({
    name: '',
    type: 'filesystem' as 'filesystem' | 'git' | 'http' | 'database' | 'custom',
    endpoint: '',
    auth_method: 'none' as 'none' | 'api_key' | 'oauth' | 'basic',
    auth_config: {} as Record<string, string>,
  });

  const resetForm = () => {
    setNewServer({
      name: '',
      type: 'filesystem',
      endpoint: '',
      auth_method: 'none',
      auth_config: {},
    });
  };

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
              MCP server management needs backend endpoint <code className="bg-blue-100 dark:bg-blue-800 px-1 rounded">/api/mcp-servers</code> to be implemented.
            </p>
          </div>
        </div>
      </div>

      {/* Server List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>MCP Servers</CardTitle>
              <CardDescription>
                Manage Model Context Protocol servers for extended capabilities
              </CardDescription>
            </div>
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
              <DialogTrigger asChild>
                <Button onClick={resetForm}>
                  <Plus className="mr-2 h-4 w-4" />
                  Add MCP Server
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl">
                <DialogHeader>
                  <DialogTitle>Add MCP Server</DialogTitle>
                  <DialogDescription>
                    Configure a new Model Context Protocol server
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="server-name">Server Name</Label>
                    <Input
                      id="server-name"
                      value={newServer.name}
                      onChange={(e) =>
                        setNewServer({ ...newServer, name: e.target.value })
                      }
                      placeholder="e.g., My Filesystem Server"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="server-type">Server Type</Label>
                    <Select
                      value={newServer.type}
                      onValueChange={(value) =>
                        setNewServer({
                          ...newServer,
                          type: value as typeof newServer.type,
                        })
                      }
                    >
                      <SelectTrigger id="server-type">
                        <SelectValue placeholder="Select type" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="filesystem">Filesystem</SelectItem>
                        <SelectItem value="git">Git</SelectItem>
                        <SelectItem value="http">HTTP</SelectItem>
                        <SelectItem value="database">Database</SelectItem>
                        <SelectItem value="custom">Custom</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="endpoint">Endpoint / URL</Label>
                    <Input
                      id="endpoint"
                      value={newServer.endpoint}
                      onChange={(e) =>
                        setNewServer({ ...newServer, endpoint: e.target.value })
                      }
                      placeholder="e.g., http://localhost:8080 or /path/to/directory"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="auth-method">Authentication</Label>
                    <Select
                      value={newServer.auth_method}
                      onValueChange={(value) =>
                        setNewServer({
                          ...newServer,
                          auth_method: value as typeof newServer.auth_method,
                        })
                      }
                    >
                      <SelectTrigger id="auth-method">
                        <SelectValue placeholder="Select auth method" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">None</SelectItem>
                        <SelectItem value="api_key">API Key</SelectItem>
                        <SelectItem value="oauth">OAuth</SelectItem>
                        <SelectItem value="basic">Basic Auth</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {newServer.auth_method === 'api_key' && (
                    <div className="space-y-2">
                      <Label htmlFor="api-key">API Key</Label>
                      <Input
                        id="api-key"
                        type="password"
                        placeholder="Enter API key"
                      />
                    </div>
                  )}

                  {newServer.auth_method === 'basic' && (
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="username">Username</Label>
                        <Input id="username" placeholder="Username" />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="password">Password</Label>
                        <Input id="password" type="password" placeholder="Password" />
                      </div>
                    </div>
                  )}

                  <div className="flex justify-end gap-3 pt-4">
                    <Button
                      variant="outline"
                      onClick={() => {
                        setDialogOpen(false);
                        resetForm();
                      }}
                    >
                      Cancel
                    </Button>
                    <Button
                      onClick={() => {
                        // TODO: Save to backend
                        setDialogOpen(false);
                        resetForm();
                      }}
                    >
                      Add Server
                    </Button>
                  </div>
                </div>
              </DialogContent>
            </Dialog>
          </div>
        </CardHeader>
        <CardContent>
          {/* Empty State */}
          <div className="text-center py-12">
            <Server className="mx-auto h-12 w-12 text-muted-foreground/50" />
            <h3 className="mt-4 text-lg font-medium text-foreground">No MCP servers configured</h3>
            <p className="mt-2 text-sm text-muted-foreground max-w-sm mx-auto">
              Add MCP servers to extend your agent's capabilities with filesystem access, Git operations, database queries, and more.
            </p>
            <div className="mt-6">
              <Button onClick={() => setDialogOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Add Your First Server
              </Button>
            </div>
          </div>

          {/* Example of what the server list would look like (commented out) */}
          {/* 
          <div className="space-y-3">
            <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg border border-border">
              <div className="flex items-center gap-3 flex-1">
                <Server className="h-5 w-5 text-muted-foreground" />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-sm">Filesystem Server</p>
                    <Badge variant="secondary" className="text-xs">filesystem</Badge>
                  </div>
                  <p className="text-xs text-muted-foreground">/path/to/workspace</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Badge>Connected</Badge>
                <Button variant="outline" size="sm">
                  <TestTube2 className="h-3 w-3" />
                </Button>
                <Button variant="outline" size="sm">
                  <Pencil className="h-3 w-3" />
                </Button>
                <Button variant="outline" size="sm">
                  <Trash2 className="h-3 w-3" />
                </Button>
              </div>
            </div>
          </div>
          */}
        </CardContent>
      </Card>

      {/* Info Card */}
      <Card>
        <CardHeader>
          <CardTitle>About MCP Servers</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>
            Model Context Protocol (MCP) servers extend your agent's capabilities by providing access to external resources and tools.
          </p>
          <ul className="list-disc list-inside space-y-1 ml-2">
            <li><strong>Filesystem:</strong> Read and write files in specific directories</li>
            <li><strong>Git:</strong> Interact with Git repositories</li>
            <li><strong>HTTP:</strong> Make API calls to external services</li>
            <li><strong>Database:</strong> Query and modify database records</li>
            <li><strong>Custom:</strong> Build your own MCP server integration</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
