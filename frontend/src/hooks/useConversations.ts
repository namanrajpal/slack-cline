/**
 * Hook for fetching and managing conversation list from backend.
 */

import { useState, useEffect, useCallback } from 'react';
import type { ConversationSummary } from '@/types/chat';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface UseConversationsOptions {
  /**
   * Number of conversations to fetch (default: 20)
   */
  limit?: number;
  /**
   * Whether to automatically fetch on mount (default: true)
   */
  autoFetch?: boolean;
}

interface UseConversationsResult {
  /**
   * List of conversation summaries
   */
  conversations: ConversationSummary[];
  /**
   * Whether conversations are currently loading
   */
  isLoading: boolean;
  /**
   * Error message if fetch failed
   */
  error: string | null;
  /**
   * Manually refresh the conversation list
   */
  refresh: () => Promise<void>;
}

export function useConversations(options: UseConversationsOptions = {}): UseConversationsResult {
  const { limit = 20, autoFetch = true } = options;

  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchConversations = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat/threads?limit=${limit}`);

      if (!response.ok) {
        throw new Error(`Failed to fetch conversations: ${response.status}`);
      }

      const data = await response.json();
      
      // Map backend response to frontend type
      const mappedConversations: ConversationSummary[] = data.conversations.map(
        (conv: {
          thread_id: string;
          channel_id: string;
          project_id?: string;
          updated_at: string;
          message_count: number;
          title: string;
          last_message_preview: string;
        }) => ({
          threadId: conv.thread_id,
          channelId: conv.channel_id,
          projectId: conv.project_id,
          updatedAt: conv.updated_at,
          messageCount: conv.message_count,
          title: conv.title,
          lastMessagePreview: conv.last_message_preview,
        })
      );

      setConversations(mappedConversations);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
      console.error('Failed to fetch conversations:', err);
    } finally {
      setIsLoading(false);
    }
  }, [limit]);

  // Auto-fetch on mount
  useEffect(() => {
    if (autoFetch) {
      fetchConversations();
    }
  }, [autoFetch, fetchConversations]);

  return {
    conversations,
    isLoading,
    error,
    refresh: fetchConversations,
  };
}
