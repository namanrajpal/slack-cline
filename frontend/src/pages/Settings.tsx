import { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import type { ApiKeyConfig } from '../types';

export default function Settings() {
  const [config, setConfig] = useState<ApiKeyConfig>({
    provider: 'anthropic',
    api_key: '',
    model_id: 'claude-sonnet-4-5-20250929',
    base_url: ''
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

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
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);

    try {
      const result = await apiClient.updateApiConfig(config);
      setMessage({
        type: 'success',
        text: result.message + (result.restart_required ? ' ⚠️ Please restart the backend service.' : '')
      });
    } catch (err) {
      setMessage({
        type: 'error',
        text: 'Failed to update configuration. Please try again.'
      });
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="text-center py-8">Loading settings...</div>;
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Settings</h2>
        <p className="mt-1 text-sm text-gray-500">
          Configure API keys and provider settings for Cline
        </p>
      </div>

      {message && (
        <div className={`rounded-md p-4 ${message.type === 'success' ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
          <p className={message.type === 'success' ? 'text-green-800' : 'text-red-800'}>
            {message.text}
          </p>
        </div>
      )}

      <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-yellow-800">
              Backend Restart Required
            </h3>
            <p className="mt-2 text-sm text-yellow-700">
              Changes to API keys require restarting the backend service to take effect.
            </p>
          </div>
        </div>
      </div>

      <div className="bg-white shadow rounded-lg">
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              LLM Provider
            </label>
            <select
              value={config.provider}
              onChange={(e) => setConfig({ ...config, provider: e.target.value })}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="anthropic">Anthropic (Claude)</option>
              <option value="openai-native">OpenAI</option>
              <option value="openrouter">OpenRouter</option>
              <option value="gemini">Google Gemini</option>
              <option value="xai">xAI (Grok)</option>
              <option value="ollama">Ollama (Local)</option>
              <option value="openai">OpenAI-Compatible</option>
            </select>
            <p className="mt-1 text-sm text-gray-500">
              Select the LLM provider you want to use
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">
              API Key
            </label>
            <input
              type="password"
              value={config.api_key}
              onChange={(e) => setConfig({ ...config, api_key: e.target.value })}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              placeholder="Enter your API key"
              required
            />
            <p className="mt-1 text-sm text-gray-500">
              Your API key will be stored securely
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">
              Model ID
            </label>
            <input
              type="text"
              value={config.model_id}
              onChange={(e) => setConfig({ ...config, model_id: e.target.value })}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              placeholder="e.g., claude-sonnet-4-5-20250929"
              required
            />
            <p className="mt-1 text-sm text-gray-500">
              Model identifier for your selected provider
            </p>
          </div>

          {(config.provider === 'openai' || config.provider === 'ollama') && (
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Base URL {config.provider === 'openai' ? '(Optional)' : '(Required for Ollama)'}
              </label>
              <input
                type="text"
                value={config.base_url}
                onChange={(e) => setConfig({ ...config, base_url: e.target.value })}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                placeholder={config.provider === 'ollama' ? 'http://localhost:11434' : 'https://your-endpoint.openai.azure.com/v1'}
              />
              <p className="mt-1 text-sm text-gray-500">
                {config.provider === 'ollama' 
                  ? 'URL of your Ollama server' 
                  : 'For OpenAI-compatible providers (Azure, etc.)'}
              </p>
            </div>
          )}

          <div className="flex justify-end space-x-3">
            <button
              type="button"
              onClick={loadConfig}
              className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
            >
              Reset
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save Configuration'}
            </button>
          </div>
        </form>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
        <h4 className="text-sm font-medium text-blue-900 mb-2">Provider Documentation</h4>
        <ul className="text-sm text-blue-700 space-y-1">
          <li>• Anthropic: <a href="https://console.anthropic.com/" className="underline" target="_blank" rel="noopener noreferrer">Get API Key</a></li>
          <li>• OpenAI: <a href="https://platform.openai.com/api-keys" className="underline" target="_blank" rel="noopener noreferrer">Get API Key</a></li>
          <li>• OpenRouter: <a href="https://openrouter.ai/keys" className="underline" target="_blank" rel="noopener noreferrer">Get API Key</a></li>
          <li>• Gemini: <a href="https://aistudio.google.com/apikey" className="underline" target="_blank" rel="noopener noreferrer">Get API Key</a></li>
        </ul>
      </div>
    </div>
  );
}
