/**
 * Custom hook for streaming chat with AG-UI event handling.
 *
 * Connects to SSE endpoint and manages message state, tool calls, and streaming.
 *
 * Key improvements:
 * - Uses robust SSE parsing via useSseStream (handles partial frames)
 * - Avoids stale closure issues by using refs for latest state
 * - Supports external threadId management for routing
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { useSseStream, type SseEvent } from './useSseStream';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  toolCalls?: ToolCall[];
  createdAt?: string;
}

export interface ToolCall {
  id: string;
  name: string;
  args?: string;
  result?: string;
  status: 'pending' | 'complete';
}

interface UseChatStreamOptions {
  apiUrl?: string;
  threadId?: string;
  onError?: (error: Error) => void;
}

export function useChatStream(options: UseChatStreamOptions = {}) {
  const {
    apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000',
    threadId: initialThreadId,
    onError,
  } = options;

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [threadId, setThreadId] = useState<string>(
    initialThreadId || crypto.randomUUID()
  );

  // Use ref to always have access to latest messages (avoids stale closure)
  const messagesRef = useRef<ChatMessage[]>(messages);
  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  // Track current streaming message
  const streamingMessageRef = useRef<ChatMessage | null>(null);

  // Use robust SSE parser
  const { stream, cancel } = useSseStream();

  // Handle incoming SSE event
  const handleSseEvent = useCallback(
    (event: SseEvent, toolCallsMap: Map<string, ToolCall>, currentMessageIdRef: { current: string | null }) => {
      console.log('[Chat] Handling event:', event.type, event);
      
      switch (event.type) {
        case 'runStarted':
          console.log('[Chat] Run started:', event);
          break;
          
        case 'runFinished':
          console.log('[Chat] Run finished:', event);
          break;
          
        case 'textMessageStart':
          currentMessageIdRef.current = event.messageId as string;
          streamingMessageRef.current = {
            id: event.messageId as string,
            role: 'assistant',
            content: '',
            toolCalls: [],
          };
          // Add message to array immediately so toolCalls can attach to it
          const newMessage = { ...streamingMessageRef.current };
          setMessages((prev) => [...prev, newMessage]);
          break;

        case 'textMessageContent':
          if (streamingMessageRef.current && event.messageId === currentMessageIdRef.current) {
            streamingMessageRef.current.content += event.delta as string;
            const updatedMessage = { ...streamingMessageRef.current };

            // Update existing message (already added on textMessageStart)
            setMessages((prev) =>
              prev.map((m) =>
                m.id === currentMessageIdRef.current ? updatedMessage : m
              )
            );
          }
          break;

        case 'textMessageEnd':
          streamingMessageRef.current = null;
          break;

        case 'toolCallStart':
          toolCallsMap.set(event.toolCallId as string, {
            id: event.toolCallId as string,
            name: event.toolName as string,
            status: 'pending',
          });
          setMessages((prev) =>
            prev.map((m) =>
              m.id === currentMessageIdRef.current
                ? { ...m, toolCalls: Array.from(toolCallsMap.values()) }
                : m
            )
          );
          break;

        case 'toolCallArgs': {
          const existingTool = toolCallsMap.get(event.toolCallId as string);
          if (existingTool) {
            existingTool.args = (existingTool.args || '') + (event.delta as string);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === currentMessageIdRef.current
                  ? { ...m, toolCalls: Array.from(toolCallsMap.values()) }
                  : m
              )
            );
          }
          break;
        }

        case 'toolCallEnd': {
          const tool = toolCallsMap.get(event.toolCallId as string);
          if (tool) {
            tool.status = 'complete';
            tool.result = event.result as string | undefined;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === currentMessageIdRef.current
                  ? { ...m, toolCalls: Array.from(toolCallsMap.values()) }
                  : m
              )
            );
          }
          break;
        }

        case 'runError':
          throw new Error((event.error as string) || 'Unknown error');
      }
    },
    []
  );

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isLoading) return;

      // Add user message immediately
      const userMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        content: text,
        createdAt: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);

      try {
        // Use ref to get latest messages (avoids stale closure)
        const currentMessages = messagesRef.current;

        // Send POST request to chat endpoint
        const response = await fetch(`${apiUrl}/api/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            threadId,
            messages: [
              ...currentMessages,
              { id: userMessage.id, role: 'user', content: text },
            ],
          }),
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        // State for this stream
        const toolCallsMap = new Map<string, ToolCall>();
        const currentMessageIdRef = { current: null as string | null };

        // Stream with robust SSE parsing
        await stream(response, (event) => {
          handleSseEvent(event, toolCallsMap, currentMessageIdRef);
        });
      } catch (error) {
        console.error('Chat error:', error);
        if (onError) {
          onError(error as Error);
        }
        // Add error message
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: `❌ Error: ${(error as Error).message}`,
          },
        ]);
      } finally {
        setIsLoading(false);
      }
    },
    [threadId, apiUrl, isLoading, onError, stream, handleSseEvent]
  );

  const clearMessages = useCallback(() => {
    cancel(); // Cancel any ongoing stream
    setMessages([]);
    setThreadId(crypto.randomUUID());
  }, [cancel]);

  // Load existing thread messages (placeholder for future implementation)
  const loadThread = useCallback(
    async (newThreadId: string) => {
      setThreadId(newThreadId);
      // TODO: Fetch existing messages from backend
      // GET /api/chat/thread/{threadId}
    },
    []
  );

  return {
    messages,
    isLoading,
    threadId,
    sendMessage,
    clearMessages,
    setThreadId,
    loadThread,
    cancel,
  };
}
