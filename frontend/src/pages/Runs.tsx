import { useEffect, useState, useRef } from 'react';
import { apiClient } from '../api/client';
import type { Run } from '../types';
import { getStatusIcon, getStatusColor, formatRelativeTime, formatDateTime } from '../utils/formatters';

interface StreamEvent {
  event_type: string;
  message: string;
  timestamp?: string;
  status?: string;
  data?: Record<string, string | boolean>;
}

export default function Runs() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('');
  
  // Panel state
  const [selectedRun, setSelectedRun] = useState<Run | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [pendingApproval, setPendingApproval] = useState(false);
  const [approvalMessage, setApprovalMessage] = useState<string | null>(null);
  const [responding, setResponding] = useState(false);
  
  const eventSourceRef = useRef<EventSource | null>(null);
  const eventsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadRuns();
    
    // Cleanup on unmount
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [statusFilter]);
  
  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    eventsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events]);

  const loadRuns = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getRuns(statusFilter ? { status: statusFilter } : {});
      setRuns(data);
    } catch (err) {
      setError('Failed to load runs');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };
  
  const handleRunClick = (run: Run) => {
    setSelectedRun(run);
    setEvents([]);
    setPendingApproval(false);
    setApprovalMessage(null);
    startEventStream(run.id);
  };
  
  const closePanel = () => {
    setSelectedRun(null);
    stopEventStream();
  };

  const startEventStream = (runId: string) => {
    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    
    setStreaming(true);
    setEvents([]);
    
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const eventSource = new EventSource(`${apiUrl}/api/runs/${runId}/events`);
    eventSourceRef.current = eventSource;
    
    eventSource.onmessage = (event) => {
      try {
        const data: StreamEvent = JSON.parse(event.data);
        setEvents(prev => [...prev, data]);
        
        // Check for approval request
        if (data.event_type === 'approval_required' || data.data?.requires_approval) {
          setPendingApproval(true);
          setApprovalMessage(data.message);
        }
        
        // Stop streaming on completion
        if (data.event_type === 'complete' || data.event_type === 'error') {
          setStreaming(false);
          setPendingApproval(false);
          eventSource.close();
          // Refresh runs list to update status
          loadRuns();
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
    setPendingApproval(false);
  };
  
  const handleRespond = async (action: 'approve' | 'deny') => {
    if (!selectedRun) return;
    
    setResponding(true);
    try {
      const response = await apiClient.respondToRun(selectedRun.id, action);
      if (response.success) {
        setPendingApproval(false);
        setApprovalMessage(null);
        setEvents(prev => [...prev, {
          event_type: 'info',
          message: `Sent ${action} response to Cline`,
          timestamp: new Date().toISOString()
        }]);
      }
    } catch (err) {
      console.error('Failed to send response:', err);
      setEvents(prev => [...prev, {
        event_type: 'error',
        message: `Failed to send ${action} response: ${err instanceof Error ? err.message : 'Unknown error'}`,
        timestamp: new Date().toISOString()
      }]);
    } finally {
      setResponding(false);
    }
  };

  if (loading) {
    return <div className="text-center py-8">Loading runs...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Runs</h2>
          <p className="mt-1 text-sm text-gray-500">
            View and monitor Cline execution history. Click any run to view logs.
          </p>
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-4 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="">All Statuses</option>
          <option value="queued">Queued</option>
          <option value="running">Running</option>
          <option value="succeeded">Succeeded</option>
          <option value="failed">Failed</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Task
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Channel
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Created
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Duration
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {runs.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-gray-500">
                  No runs found. Try the Admin Panel to test a run.
                </td>
              </tr>
            ) : (
              runs.map((run) => (
                <tr 
                  key={run.id} 
                  className={`hover:bg-gray-50 transition-colors ${
                    selectedRun?.id === run.id ? 'bg-blue-50' : ''
                  }`}
                >
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(run.status)}`}>
                      {getStatusIcon(run.status)} {run.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">
                    <div className="max-w-md truncate">
                      {run.task_prompt}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {run.slack_channel_id}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    <div>{formatRelativeTime(run.created_at)}</div>
                    <div className="text-xs text-gray-400">{formatDateTime(run.created_at)}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {run.started_at && run.finished_at ? (
                      <>
                        {Math.round((new Date(run.finished_at).getTime() - new Date(run.started_at).getTime()) / 1000)}s
                      </>
                    ) : run.started_at ? (
                      'In progress...'
                    ) : (
                      'Not started'
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    <button
                      onClick={() => handleRunClick(run)}
                      className="inline-flex items-center px-3 py-1.5 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
                      title="View logs"
                    >
                      <svg className="w-4 h-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      Logs
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {runs.length > 0 && (
        <div className="text-center text-sm text-gray-500">
          Showing {runs.length} run{runs.length !== 1 ? 's' : ''}
        </div>
      )}

      {/* Side Panel - Slides in from left */}
      {selectedRun && (
        <>
          {/* Backdrop */}
          <div 
            className="fixed inset-0 bg-black bg-opacity-50 z-40 transition-opacity"
            onClick={closePanel}
          />
          
          {/* Panel */}
          <div className="fixed left-0 top-0 h-full w-full md:w-2/5 bg-white shadow-2xl z-50 flex flex-col slide-from-left-side">
            {/* Run Details (10-15% - Fixed) */}
            <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white px-6 py-4 flex-shrink-0">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-2 mb-2">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      selectedRun.status === 'succeeded' ? 'bg-green-500' :
                      selectedRun.status === 'failed' ? 'bg-red-500' :
                      selectedRun.status === 'running' ? 'bg-yellow-500' :
                      selectedRun.status === 'cancelled' ? 'bg-gray-500' :
                      'bg-blue-500'
                    }`}>
                      {getStatusIcon(selectedRun.status)} {selectedRun.status.toUpperCase()}
                    </span>
                  </div>
                  <h3 className="text-lg font-semibold mb-1 truncate">
                    {selectedRun.task_prompt}
                  </h3>
                  <div className="text-sm text-blue-100 space-y-1">
                    <p>Channel: {selectedRun.slack_channel_id}</p>
                    <p>Created: {formatRelativeTime(selectedRun.created_at)}</p>
                    {selectedRun.started_at && selectedRun.finished_at && (
                      <p>Duration: {Math.round((new Date(selectedRun.finished_at).getTime() - new Date(selectedRun.started_at).getTime()) / 1000)}s</p>
                    )}
                  </div>
                </div>
                <button
                  onClick={closePanel}
                  className="ml-4 text-white hover:text-gray-200 transition-colors"
                >
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Live Output (75-80% - Scrollable) */}
            <div className="flex-1 overflow-hidden flex flex-col bg-gray-950">
              <div className="px-4 py-3 border-b border-gray-700 flex items-center justify-between bg-gray-900">
                <div className="flex items-center">
                  <span className="text-green-400 font-medium text-sm">Live Output</span>
                  {streaming && (
                    <span className="ml-2 flex items-center text-yellow-400 text-xs">
                      <span className="animate-pulse mr-1">●</span>
                      Streaming...
                    </span>
                  )}
                  {pendingApproval && (
                    <span className="ml-2 flex items-center text-orange-400 text-xs">
                      <span className="animate-pulse mr-1">⏳</span>
                      Waiting for approval
                    </span>
                  )}
                </div>
                {streaming && (
                  <button
                    onClick={stopEventStream}
                    className="px-2 py-1 text-xs bg-red-600 hover:bg-red-700 text-white rounded"
                  >
                    Stop
                  </button>
                )}
              </div>
              
              {/* Approval Banner */}
              {pendingApproval && (
                <div className="px-4 py-3 bg-orange-900 border-b border-orange-700 flex-shrink-0">
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <p className="text-orange-200 font-medium text-sm">
                        🔔 Cline needs your approval
                      </p>
                      {approvalMessage && (
                        <p className="text-orange-300 text-xs mt-1 font-mono truncate">
                          {approvalMessage}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              )}
              
              {/* Log Output */}
              <div className="flex-1 overflow-y-auto p-4 font-mono text-xs">
                {events.length === 0 ? (
                  <div className="text-gray-500 text-center py-8">
                    {streaming ? 'Waiting for events...' : 'No events yet'}
                  </div>
                ) : (
                  events.map((event, index) => (
                    <div 
                      key={index} 
                      className={`py-1 ${
                        event.event_type === 'error' ? 'text-red-400' :
                        event.event_type === 'complete' ? 'text-green-400' :
                        event.event_type === 'connected' ? 'text-blue-400' :
                        event.event_type === 'status' ? 'text-yellow-400' :
                        event.event_type === 'approval_required' ? 'text-orange-400 bg-orange-900/30 px-2 rounded' :
                        event.event_type === 'info' ? 'text-cyan-400' :
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
                        event.event_type === 'approval_required' ? 'text-orange-400' :
                        event.event_type === 'info' ? 'text-cyan-400' :
                        'text-gray-500'
                      }`}>
                        [{event.event_type}]
                      </span>
                      {event.message}
                    </div>
                  ))
                )}
                <div ref={eventsEndRef} />
              </div>
            </div>

            {/* Action Buttons (10% - Conditional) */}
            {pendingApproval && (
              <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex-shrink-0">
                <div className="flex space-x-3">
                  <button
                    onClick={() => handleRespond('approve')}
                    disabled={responding}
                    className="flex-1 px-4 py-2 text-sm bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white rounded-md font-medium flex items-center justify-center"
                  >
                    {responding ? '...' : '✅ Approve'}
                  </button>
                  <button
                    onClick={() => handleRespond('deny')}
                    disabled={responding}
                    className="flex-1 px-4 py-2 text-sm bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white rounded-md font-medium flex items-center justify-center"
                  >
                    {responding ? '...' : '❌ Deny'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </>
      )}

      <style>{`
        @keyframes slideFromLeftSide {
          from {
            transform: translateX(-100%);
          }
          to {
            transform: translateX(0);
          }
        }
        .slide-from-left-side {
          animation: slideFromLeftSide 0.3s ease-out;
        }
      `}</style>
    </div>
  );
}
