import { useEffect, useState, useRef } from 'react';
import { apiClient } from '../api/client';
import type { Project, TestSlackRequest, TestSlackResponse } from '../types';

interface StreamEvent {
  event_type: string;
  message: string;
  timestamp?: string;
  status?: string;
  data?: Record<string, string>;
}

export default function AdminPanel() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [formData, setFormData] = useState<TestSlackRequest>({
    channel_id: '',
    text: '',
    user_id: 'U_TEST_USER',
    user_name: 'test_user',
    command: '/cline',
    team_id: 'T_TEST_TEAM',
    team_domain: 'test-workspace'
  });
  const [testing, setTesting] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [result, setResult] = useState<TestSlackResponse | null>(null);
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const eventsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadProjects();
    
    // Cleanup on unmount
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);
  
  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    eventsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events]);

  const loadProjects = async () => {
    try {
      const data = await apiClient.getProjects();
      setProjects(data);
      if (data.length > 0 && !formData.channel_id) {
        setFormData(prev => ({ ...prev, channel_id: data[0].slack_channel_id }));
      }
    } catch (err) {
      console.error('Failed to load projects:', err);
    }
  };

  const startEventStream = (runId: string) => {
    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    
    setStreaming(true);
    setEvents([]);
    setCurrentRunId(runId);
    
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const eventSource = new EventSource(`${apiUrl}/api/runs/${runId}/events`);
    eventSourceRef.current = eventSource;
    
    eventSource.onmessage = (event) => {
      try {
        const data: StreamEvent = JSON.parse(event.data);
        setEvents(prev => [...prev, data]);
        
        // Stop streaming on completion
        if (data.event_type === 'complete' || data.event_type === 'error') {
          setStreaming(false);
          eventSource.close();
        }
      } catch (err) {
        console.error('Failed to parse event:', err);
      }
    };
    
    eventSource.onerror = () => {
      setStreaming(false);
      eventSource.close();
      setEvents(prev => [...prev, {
        event_type: 'error',
        message: 'Connection lost'
      }]);
    };
  };
  
  const stopEventStream = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setStreaming(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setTesting(true);
    setResult(null);
    setEvents([]);
    setCurrentRunId(null);

    try {
      const response = await apiClient.simulateSlackCommand(formData);
      setResult(response);
      
      // Extract run_id from response payload if available
      const runId = response.response_payload?.run_id;
      if (runId && response.success) {
        // Start streaming events for this run
        startEventStream(runId);
      }
    } catch (err) {
      setResult({
        success: false,
        message: 'Request failed: ' + (err instanceof Error ? err.message : 'Unknown error'),
        run_id: undefined,
        request_payload: undefined,
        response_payload: undefined
      });
    } finally {
      setTesting(false);
    }
  };

  const handleQuickFill = (task: string) => {
    setFormData(prev => ({ ...prev, text: `run ${task}` }));
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Admin Testing Panel</h2>
        <p className="mt-1 text-sm text-gray-500">
          Simulate Slack commands for testing without using actual Slack
        </p>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-blue-800">
              How it works
            </h3>
            <p className="mt-2 text-sm text-blue-700">
              This panel simulates Slack webhook calls with proper authentication. 
              It calls the actual <code className="bg-blue-100 px-1 rounded">/slack/events</code> endpoint,
              so you're testing the full integration flow without needing Slack.
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Form */}
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Test Command</h3>
          
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Channel (Project)
              </label>
              <select
                value={formData.channel_id}
                onChange={(e) => setFormData({ ...formData, channel_id: e.target.value })}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                required
              >
                <option value="">Select a channel...</option>
                {projects.map((project) => (
                  <option key={project.id} value={project.slack_channel_id}>
                    {project.slack_channel_id} ({project.repo_url.split('/').pop()})
                  </option>
                ))}
              </select>
              {projects.length === 0 && (
                <p className="mt-1 text-sm text-red-600">
                  No projects found. Create one in the Projects page first.
                </p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Task Description
              </label>
              <textarea
                value={formData.text.replace(/^run\s+/, '')}
                onChange={(e) => setFormData({ ...formData, text: `run ${e.target.value}` })}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                rows={3}
                placeholder="e.g., create a hello world Python script"
                required
              />
              <p className="mt-1 text-sm text-gray-500">
                Full command: <code className="bg-gray-100 px-1 rounded">/cline run {formData.text.replace(/^run\s+/, '')}</code>
              </p>
            </div>

            <div className="border-t border-gray-200 pt-4">
              <p className="text-sm font-medium text-gray-700 mb-2">Quick Fill:</p>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => handleQuickFill('create a README file')}
                  className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-md"
                >
                  Create README
                </button>
                <button
                  type="button"
                  onClick={() => handleQuickFill('add unit tests')}
                  className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-md"
                >
                  Add Tests
                </button>
                <button
                  type="button"
                  onClick={() => handleQuickFill('fix linting errors')}
                  className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-md"
                >
                  Fix Linting
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={testing || projects.length === 0}
              className="w-full px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
            >
              {testing ? '🔄 Simulating...' : '▶️ Simulate Slack Command'}
            </button>
          </form>
        </div>

        {/* Results */}
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Results</h3>
          
          {!result ? (
            <div className="text-center py-12 text-gray-500">
              <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p className="mt-2">Submit a command to see results here</p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className={`rounded-md p-4 ${result.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
                <div className="flex items-center">
                  <span className="text-2xl mr-2">{result.success ? '✅' : '❌'}</span>
                  <div>
                    <p className={`font-medium ${result.success ? 'text-green-800' : 'text-red-800'}`}>
                      {result.success ? 'Command Executed Successfully' : 'Command Failed'}
                    </p>
                    <p className={`text-sm ${result.success ? 'text-green-700' : 'text-red-700'}`}>
                      {result.message}
                    </p>
                  </div>
                </div>
              </div>

              {currentRunId && (
                <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
                  <p className="text-sm font-medium text-blue-900">Run ID:</p>
                  <p className="text-sm text-blue-700 font-mono">{currentRunId}</p>
                </div>
              )}

              <div className="flex space-x-2 pt-2">
                <button
                  onClick={() => { setResult(null); setEvents([]); stopEventStream(); }}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Clear Results
                </button>
                <a
                  href="/runs"
                  className="flex-1 px-3 py-2 bg-blue-600 text-white rounded-md text-sm font-medium text-center hover:bg-blue-700"
                >
                  View Runs →
                </a>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Live Output */}
      {(events.length > 0 || streaming) && (
        <div className="bg-gray-900 shadow rounded-lg overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-700 flex items-center justify-between">
            <div className="flex items-center">
              <span className="text-green-400 font-medium">Live Output</span>
              {streaming && (
                <span className="ml-2 flex items-center text-yellow-400 text-sm">
                  <span className="animate-pulse mr-1">●</span>
                  Streaming...
                </span>
              )}
            </div>
            {streaming && (
              <button
                onClick={stopEventStream}
                className="px-3 py-1 text-sm bg-red-600 hover:bg-red-700 text-white rounded-md"
              >
                Stop
              </button>
            )}
          </div>
          <div className="p-4 font-mono text-sm max-h-96 overflow-y-auto bg-gray-950">
            {events.map((event, index) => (
              <div 
                key={index} 
                className={`py-1 ${
                  event.event_type === 'error' ? 'text-red-400' :
                  event.event_type === 'complete' ? 'text-green-400' :
                  event.event_type === 'connected' ? 'text-blue-400' :
                  event.event_type === 'status' ? 'text-yellow-400' :
                  'text-gray-300'
                }`}
              >
                <span className="text-gray-500 mr-2">
                  {event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : ''}
                </span>
                <span className={`mr-2 ${
                  event.event_type === 'step' ? 'text-cyan-400' :
                  event.event_type === 'complete' ? 'text-green-400' :
                  event.event_type === 'error' ? 'text-red-400' :
                  'text-gray-500'
                }`}>
                  [{event.event_type}]
                </span>
                {event.message}
              </div>
            ))}
            <div ref={eventsEndRef} />
          </div>
        </div>
      )}

      {/* Instructions */}
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Testing Instructions</h3>
        <div className="prose prose-sm max-w-none text-gray-600">
          <ol className="space-y-2">
            <li>
              <strong>Create a project</strong> in the Projects page if you haven't already
            </li>
            <li>
              <strong>Select a channel</strong> from the dropdown above
            </li>
            <li>
              <strong>Enter a task description</strong> (e.g., "create a README file")
            </li>
            <li>
              <strong>Click "Simulate Slack Command"</strong> to test the integration
            </li>
            <li>
              <strong>Check the Runs page</strong> to see the execution status
            </li>
          </ol>
          <p className="mt-4 text-sm">
            <strong>Note:</strong> This simulation calls the actual <code>/slack/events</code> endpoint
            with proper Slack signature verification, so you're testing the real integration flow.
          </p>
        </div>
      </div>
    </div>
  );
}
