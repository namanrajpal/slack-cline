import { useEffect, useState } from 'react';
import { apiClient } from '@/api/client';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useToast } from '@/components/ui/use-toast';
import { AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';
import type { ApiKeyConfig } from '@/types';

export default function ProvidersTab() {
  const [config, setConfig] = useState<ApiKeyConfig>({
    provider: 'anthropic',
    api_key: '',
    model_id: 'claude-sonnet-4-5-20250929',
    base_url: ''
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      setLoading(true);
      const data = await apiClient.getApiConfig();
      setConfig(data);
    } catch (err) {
      console.error('Failed to load config:', err);
      toast({
        title: 'Error',
        description: 'Failed to load provider configuration',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);

    try {
      const result = await apiClient.updateApiConfig(config);
      toast({
        title: 'Success',
        description: result.restart_required 
          ? '⚠️ Configuration saved. Please restart the backend service.'
          : 'Configuration saved successfully',
      });
    } catch (err) {
      toast({
        title: 'Error',
        description: 'Failed to update configuration',
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
      {/* Warning Banner */}
      <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
        <div className="flex gap-3">
          <AlertCircle className="h-5 w-5 text-yellow-600 dark:text-yellow-500 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
              Backend Restart Required
            </h3>
            <p className="mt-1 text-sm text-yellow-700 dark:text-yellow-300">
              Changes to API keys require restarting the backend service to take effect.
            </p>
          </div>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Provider Selection */}
        <Card>
          <CardHeader>
            <CardTitle>Current Provider</CardTitle>
            <CardDescription>
              Select your LLM provider and configure the model settings
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="provider">LLM Provider</Label>
              <Select
                value={config.provider}
                onValueChange={(value) => setConfig({ ...config, provider: value })}
              >
                <SelectTrigger id="provider">
                  <SelectValue placeholder="Select provider" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="anthropic">Anthropic (Claude)</SelectItem>
                  <SelectItem value="openai-native">OpenAI</SelectItem>
                  <SelectItem value="openrouter">OpenRouter</SelectItem>
                  <SelectItem value="gemini">Google Gemini</SelectItem>
                  <SelectItem value="xai">xAI (Grok)</SelectItem>
                  <SelectItem value="ollama">Ollama (Local)</SelectItem>
                  <SelectItem value="openai">OpenAI-Compatible</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-sm text-muted-foreground">
                Choose the LLM provider you want to use
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="model_id">Model ID</Label>
              <Input
                id="model_id"
                type="text"
                value={config.model_id}
                onChange={(e) => setConfig({ ...config, model_id: e.target.value })}
                placeholder="e.g., claude-sonnet-4-5-20250929"
                required
              />
              <p className="text-sm text-muted-foreground">
                Model identifier for your selected provider
              </p>
            </div>

            {(config.provider === 'openai' || config.provider === 'ollama') && (
              <div className="space-y-2">
                <Label htmlFor="base_url">
                  Base URL {config.provider === 'ollama' ? '(Required)' : '(Optional)'}
                </Label>
                <Input
                  id="base_url"
                  type="text"
                  value={config.base_url || ''}
                  onChange={(e) => setConfig({ ...config, base_url: e.target.value })}
                  placeholder={
                    config.provider === 'ollama'
                      ? 'http://localhost:11434'
                      : 'https://your-endpoint.openai.azure.com/v1'
                  }
                />
                <p className="text-sm text-muted-foreground">
                  {config.provider === 'ollama'
                    ? 'URL of your Ollama server'
                    : 'For OpenAI-compatible providers (Azure, etc.)'}
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* API Keys */}
        <Card>
          <CardHeader>
            <CardTitle>API Credentials</CardTitle>
            <CardDescription>
              Your API key will be stored securely on the backend
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="api_key">API Key</Label>
                <button
                  type="button"
                  onClick={() => setShowApiKey(!showApiKey)}
                  className="text-sm text-primary hover:text-primary/80"
                >
                  {showApiKey ? 'Hide' : 'Show'}
                </button>
              </div>
              <Input
                id="api_key"
                type={showApiKey ? 'text' : 'password'}
                value={config.api_key}
                onChange={(e) => setConfig({ ...config, api_key: e.target.value })}
                placeholder="Enter your API key"
                required
              />
              <p className="text-sm text-muted-foreground">
                Your credentials are encrypted and stored securely
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Actions */}
        <div className="flex items-center justify-between">
          <Button
            type="button"
            variant="outline"
            onClick={loadConfig}
            disabled={saving}
          >
            Reset
          </Button>
          <div className="flex gap-3">
            <Button
              type="button"
              variant="secondary"
              disabled
            >
              Test Connection
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
        </div>
      </form>

      {/* Provider Documentation */}
      <Card>
        <CardHeader>
          <CardTitle>Provider Documentation</CardTitle>
          <CardDescription>
            Get your API keys from these providers
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm">
            <li>
              <strong>Anthropic:</strong>{' '}
              <a
                href="https://console.anthropic.com/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline"
              >
                Get API Key →
              </a>
            </li>
            <li>
              <strong>OpenAI:</strong>{' '}
              <a
                href="https://platform.openai.com/api-keys"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline"
              >
                Get API Key →
              </a>
            </li>
            <li>
              <strong>OpenRouter:</strong>{' '}
              <a
                href="https://openrouter.ai/keys"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline"
              >
                Get API Key →
              </a>
            </li>
            <li>
              <strong>Gemini:</strong>{' '}
              <a
                href="https://aistudio.google.com/apikey"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline"
              >
                Get API Key →
              </a>
            </li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
