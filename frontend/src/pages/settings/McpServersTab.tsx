import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Plus, Server, Pencil, Trash2, Loader2 } from 'lucide-react';
import { apiClient } from '@/api/client';
import type { McpServer, McpServerCreate } from '@/types';
import { useToast } from '@/components/ui/use-toast';

export default function McpServersTab() {
  const { toast } = useToast();
  const [servers, setServers] = useState<McpServer[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingServer, setEditingServer] = useState<McpServer | null>(null);
  const [formData, setFormData] = useState<McpServerCreate>({
    name: '',
    type: 'stdio',
    url: '',
  });
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    loadServers();
  }, []);

  const loadServers = async () => {
    try {
      setLoading(true);
      const data = await apiClient.getMcpServers();
      setServers(data);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to load MCP servers',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      type: 'stdio',
      url: '',
    });
    setEditingServer(null);
  };

  const handleOpenDialog = (server?: McpServer) => {
    if (server) {
      setEditingServer(server);
      setFormData({
        name: server.name,
        type: server.type,
        url: server.url,
      });
    } else {
      resetForm();
    }
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    resetForm();
  };

  const handleSubmit = async () => {
    if (!formData.name.trim() || !formData.url.trim()) {
      toast({
        title: 'Validation Error',
        description: 'Name and URL are required',
        variant: 'destructive',
      });
      return;
    }

    try {
      setSubmitting(true);
      if (editingServer) {
        await apiClient.updateMcpServer(editingServer.id, formData);
        toast({
          title: 'Success',
          description: 'MCP server updated successfully',
        });
      } else {
        await apiClient.createMcpServer(formData);
        toast({
          title: 'Success',
          description: 'MCP server created successfully',
        });
      }
      handleCloseDialog();
      loadServers();
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to save MCP server',
        variant: 'destructive',
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (server: McpServer) => {
    if (!confirm(`Are you sure you want to delete "${server.name}"?`)) {
      return;
    }

    try {
      await apiClient.deleteMcpServer(server.id);
      toast({
        title: 'Success',
        description: 'MCP server deleted successfully',
      });
      loadServers();
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to delete MCP server',
        variant: 'destructive',
      });
    }
  };

  return (
    <div className="space-y-6">
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
                <Button onClick={() => handleOpenDialog()}>
                  <Plus className="mr-2 h-4 w-4" />
                  Add MCP Server
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl">
                <DialogHeader>
                  <DialogTitle>
                    {editingServer ? 'Edit MCP Server' : 'Add MCP Server'}
                  </DialogTitle>
                  <DialogDescription>
                    Configure a Model Context Protocol server
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="server-name">Server Name *</Label>
                    <Input
                      id="server-name"
                      value={formData.name}
                      onChange={(e) =>
                        setFormData({ ...formData, name: e.target.value })
                      }
                      placeholder="e.g., My MCP Server"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="server-type">Server Type *</Label>
                    <Select
                      value={formData.type}
                      onValueChange={(value: 'stdio' | 'http') =>
                        setFormData({ ...formData, type: value })
                      }
                    >
                      <SelectTrigger id="server-type">
                        <SelectValue placeholder="Select type" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="stdio">STDIO</SelectItem>
                        <SelectItem value="http">HTTP</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="server-url">Server URL *</Label>
                    <Input
                      id="server-url"
                      value={formData.url}
                      onChange={(e) =>
                        setFormData({ ...formData, url: e.target.value })
                      }
                      placeholder="e.g., http://localhost:8080 or /path/to/command"
                    />
                    <p className="text-xs text-muted-foreground">
                      For stdio: path to executable. For http: HTTP endpoint URL.
                    </p>
                  </div>

                  <div className="flex justify-end gap-3 pt-4">
                    <Button
                      variant="outline"
                      onClick={handleCloseDialog}
                      disabled={submitting}
                    >
                      Cancel
                    </Button>
                    <Button onClick={handleSubmit} disabled={submitting}>
                      {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                      {editingServer ? 'Update' : 'Add'} Server
                    </Button>
                  </div>
                </div>
              </DialogContent>
            </Dialog>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : servers.length === 0 ? (
            <div className="text-center py-12">
              <Server className="mx-auto h-12 w-12 text-muted-foreground/50" />
              <h3 className="mt-4 text-lg font-medium text-foreground">No MCP servers configured</h3>
              <p className="mt-2 text-sm text-muted-foreground max-w-sm mx-auto">
                Add MCP servers to extend your agent's capabilities with external resources and tools.
              </p>
              <div className="mt-6">
                <Button onClick={() => handleOpenDialog()}>
                  <Plus className="mr-2 h-4 w-4" />
                  Add Your First Server
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {servers.map((server) => (
                <div
                  key={server.id}
                  className="flex items-center justify-between p-4 bg-muted/50 rounded-lg border border-border"
                >
                  <div className="flex items-center gap-3 flex-1">
                    <Server className="h-5 w-5 text-muted-foreground" />
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <p className="font-medium text-sm">{server.name}</p>
                        <Badge variant="secondary" className="text-xs">
                          {server.type === 'stdio' ? 'STDIO' : 'HTTP'}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">{server.url}</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        Created: {new Date(server.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleOpenDialog(server)}
                    >
                      <Pencil className="h-3 w-3" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDelete(server)}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
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
            <li><strong>STDIO:</strong> Connect to a command-line program via standard input/output</li>
            <li><strong>HTTP:</strong> Connect to an HTTP-based MCP server endpoint</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
