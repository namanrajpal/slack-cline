/**
 * Chat-related types for the dedicated Chat page.
 */

export interface ConversationSummary {
  threadId: string;
  channelId: string;
  projectId?: string;
  updatedAt: string;
  messageCount: number;
  title: string;
  lastMessagePreview: string;
}

export interface ChatRouteParams {
  threadId?: string;
}

export type ChatMessageRole = 'user' | 'assistant';

export interface ChatMessage {
  id: string;
  role: ChatMessageRole;
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

/**
 * Chat page state modes
 */
export type ChatMode = 'empty' | 'chat';

/**
 * Prompt suggestion for empty state
 */
export interface PromptSuggestion {
  id: string;
  title: string;
  description?: string;
  prompt: string;
}
