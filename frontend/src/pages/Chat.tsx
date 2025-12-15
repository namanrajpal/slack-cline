/**
 * Chat Page - ChatGPT-style dedicated chat interface.
 *
 * Features:
 * - Empty state: centered input with prompt suggestions
 * - Chat state: transcript above with sticky input at bottom
 * - Controlled auto-scroll (only when near bottom)
 * - Robust SSE streaming
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Send, ArrowDown, Sparkles, Code, FileSearch, Bug } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import { useChatStream } from '@/hooks/useChatStream';
import { useAutoScroll } from '@/hooks/useAutoScroll';
import { ChatMessage as ChatMessageComponent } from '@/components/chat/ChatMessage';
import { useToast } from '@/components/ui/use-toast';
import type { ChatMode, PromptSuggestion } from '@/types/chat';

const PROMPT_SUGGESTIONS: PromptSuggestion[] = [
  {
    id: '1',
    title: 'Explore codebase',
    description: 'Understand the project structure',
    prompt: 'What does this project do? Give me an overview of the main components and architecture.',
  },
  {
    id: '2',
    title: 'Find a bug',
    description: 'Help debug an issue',
    prompt: 'I have an issue where ',
  },
  {
    id: '3',
    title: 'Refactor code',
    description: 'Improve code quality',
    prompt: 'Help me refactor ',
  },
  {
    id: '4',
    title: 'Write tests',
    description: 'Add test coverage',
    prompt: 'Write tests for ',
  },
];

const SUGGESTION_ICONS: Record<string, typeof Sparkles> = {
  '1': FileSearch,
  '2': Bug,
  '3': Code,
  '4': Sparkles,
};

export default function Chat() {
  const { threadId: routeThreadId } = useParams<{ threadId?: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();

  // Chat state
  const [inputValue, setInputValue] = useState('');
  const [mode, setMode] = useState<ChatMode>('empty');

  // Refs
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll hook
  const {
    containerRef: scrollContainerRef,
    endRef: messagesEndRef,
    isAtBottom,
    scrollToBottom,
    onScroll: handleScroll,
    resetUserScroll,
  } = useAutoScroll({ thresholdPx: 100 });

  // Initialize chat stream hook
  const { messages, isLoading, threadId, sendMessage, setThreadId } = useChatStream({
    threadId: routeThreadId,
    onError: (error) => {
      toast({
        title: 'Chat Error',
        description: error.message,
        variant: 'destructive',
      });
    },
  });

  // Update mode based on messages
  useEffect(() => {
    if (messages.length > 0) {
      setMode('chat');
    }
  }, [messages]);

  // Update URL when threadId changes (after first message)
  useEffect(() => {
    if (threadId && messages.length > 0 && !routeThreadId) {
      navigate(`/chat/${threadId}`, { replace: true });
    }
  }, [threadId, messages.length, routeThreadId, navigate]);

  // Set threadId from route param
  useEffect(() => {
    if (routeThreadId && routeThreadId !== threadId) {
      setThreadId(routeThreadId);
    }
  }, [routeThreadId, threadId, setThreadId]);

  // Auto-scroll when messages change (only if at bottom)
  useEffect(() => {
    if (isAtBottom && messages.length > 0) {
      requestAnimationFrame(() => {
        scrollToBottom('instant');
      });
    }
  }, [messages, isAtBottom, scrollToBottom]);

  // Handle send
  const handleSend = useCallback(async () => {
    const text = inputValue.trim();
    if (!text || isLoading) return;

    setInputValue('');
    resetUserScroll();

    // Scroll to bottom on send
    setTimeout(() => scrollToBottom('instant'), 50);

    await sendMessage(text);
  }, [inputValue, isLoading, sendMessage, scrollToBottom, resetUserScroll]);

  // Handle key press
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  // Handle suggestion click
  const handleSuggestionClick = useCallback((suggestion: PromptSuggestion) => {
    setInputValue(suggestion.prompt);
    inputRef.current?.focus();
  }, []);

  // Render empty state
  const renderEmptyState = () => (
    <div className="flex flex-col items-center flex-1 p-6 pt-[15vh] max-w-3xl mx-auto w-full">
      {/* Logo */}
      <div className="mb-10">
        <img 
          src="/sline-logo.png" 
          alt="Sline" 
          className="h-16 w-16"
        />
      </div>

      {/* Suggestions Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full mb-8">
        {PROMPT_SUGGESTIONS.map((suggestion) => {
          const Icon = SUGGESTION_ICONS[suggestion.id] || Sparkles;
          return (
            <button
              key={suggestion.id}
              onClick={() => handleSuggestionClick(suggestion)}
              className="flex items-start gap-3 p-4 rounded-lg border border-border bg-card hover:bg-accent hover:border-accent-foreground/20 transition-all text-left group"
            >
              <div className="h-8 w-8 rounded-md bg-primary/10 flex items-center justify-center flex-shrink-0 group-hover:bg-primary/20 transition-colors">
                <Icon className="h-4 w-4 text-primary" />
              </div>
              <div>
                <p className="font-medium text-foreground text-sm">{suggestion.title}</p>
                {suggestion.description && (
                  <p className="text-xs text-muted-foreground mt-0.5">{suggestion.description}</p>
                )}
              </div>
            </button>
          );
        })}
      </div>

      {/* Input area */}
      <div className="w-full">
        {renderComposer()}
      </div>
    </div>
  );

  // Render chat transcript
  const renderTranscript = () => (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Messages area */}
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto pb-32"
      >
        <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
          {messages.map((message) => (
            <ChatMessageComponent key={message.id} message={message} />
          ))}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Scroll to bottom button */}
      {!isAtBottom && mode === 'chat' && (
        <div className="absolute bottom-28 left-1/2 -translate-x-1/2 z-10">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => scrollToBottom('smooth')}
            className="rounded-full shadow-lg gap-1.5"
          >
            <ArrowDown className="h-4 w-4" />
            Scroll to bottom
          </Button>
        </div>
      )}

      {/* Sticky input - fixed at bottom */}
      <div className="absolute bottom-0 left-0 right-0 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="max-w-3xl mx-auto px-4 py-4">
          {renderComposer()}
        </div>
      </div>
    </div>
  );

  // Render composer (input area)
  const renderComposer = () => (
    <div className="relative">
      <Textarea
        ref={inputRef}
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask about your code..."
        disabled={isLoading}
        className={cn(
          'min-h-[52px] max-h-[200px] resize-none pr-12 py-3',
          'bg-muted/50 border-border',
          'focus-visible:ring-0 focus-visible:ring-offset-0 focus-visible:border-border',
          'placeholder:text-muted-foreground/60'
        )}
        rows={1}
      />
      <Button
        onClick={handleSend}
        disabled={isLoading || !inputValue.trim()}
        size="icon"
        className="absolute right-2 bottom-2 h-8 w-8 rounded-md"
      >
        <Send className="h-4 w-4" />
      </Button>
    </div>
  );

  return (
    <div className="flex flex-col h-full relative">
      {mode === 'empty' ? renderEmptyState() : renderTranscript()}
    </div>
  );
}
