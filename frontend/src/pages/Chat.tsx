/**
 * Chat Page - ChatGPT-style dedicated chat interface.
 *
 * Features:
 * - Empty state: centered input with prompt suggestions
 * - Chat state: transcript above with sticky input at bottom
 * - Controlled auto-scroll (only when near bottom)
 * - Robust SSE streaming
 * - Polished composer with blocks.so patterns
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  ArrowDown, 
  Sparkles, 
  Code, 
  FileSearch, 
  Bug, 
  ArrowUp,
  Plus,
  Paperclip,
  Link,
  Clipboard,
  FileText,
  Settings2,
  Loader2,
  Github
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { cn } from '@/lib/utils';
import { useChatStream } from '@/hooks/useChatStream';
import { useAutoScroll } from '@/hooks/useAutoScroll';
import { ChatMessage as ChatMessageComponent } from '@/components/chat/ChatMessage';
import { useToast } from '@/components/ui/use-toast';
import type { ChatMode, PromptSuggestion } from '@/types/chat';
import type { Project } from '@/types';
import { apiClient } from '@/api/client';

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

  // Project selection state
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);

  // Refs
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const loadedThreadRef = useRef<string | null>(null);
  const previousRouteThreadIdRef = useRef<string | undefined>(routeThreadId);

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
  const { messages, isLoading, threadId, sendMessage, setThreadId, loadThread, clearMessages } = useChatStream({
    threadId: routeThreadId,
    onError: (error) => {
      toast({
        title: 'Chat Error',
        description: error.message,
        variant: 'destructive',
      });
    },
  });

  // Load projects on mount
  useEffect(() => {
    const loadProjects = async () => {
      try {
        const projectsData = await apiClient.getProjects();
        setProjects(projectsData);
      } catch (error) {
        console.error('Failed to load projects:', error);
        toast({
          title: 'Failed to load projects',
          description: 'Could not fetch project list',
          variant: 'destructive',
        });
      }
    };
    
    loadProjects();
  }, [toast]);

  // Update mode based on messages
  useEffect(() => {
    if (messages.length > 0) {
      setMode('chat');
    }
  }, [messages]);

  // Clear messages when navigating TO /chat (not during active conversation)
  useEffect(() => {
    // Only clear if we actually NAVIGATED to /chat (route changed from having threadId to not having one)
    const routeChanged = previousRouteThreadIdRef.current !== routeThreadId;
    
    if (routeChanged && !routeThreadId && messages.length > 0) {
      console.log('[Chat] Route changed to /chat, clearing messages');
      clearMessages();
      loadedThreadRef.current = null;
    }
    
    // Update the ref for next comparison
    previousRouteThreadIdRef.current = routeThreadId;
  }, [routeThreadId]); // Remove messages.length and clearMessages from deps to prevent loop

  // Load thread from route param (only if no messages yet)
  useEffect(() => {
    if (routeThreadId && 
        loadedThreadRef.current !== routeThreadId &&
        messages.length === 0) {
      loadedThreadRef.current = routeThreadId;
      loadThread(routeThreadId);
    }
  }, [routeThreadId, messages.length, loadThread]);

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

    // Pass selectedProjectId to backend (dashboard-specific context)
    await sendMessage(text, selectedProjectId);
  }, [inputValue, isLoading, sendMessage, scrollToBottom, resetUserScroll, selectedProjectId]);

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
    <div className="flex flex-col min-h-[calc(100vh-6rem)]">
      {/* Messages area - scrollable */}
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto pb-28"
      >
        <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
          {messages.map((message) => (
            <ChatMessageComponent key={message.id} message={message} />
          ))}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Scroll to bottom button - fixed position */}
      {!isAtBottom && mode === 'chat' && (
        <div className="fixed bottom-28 left-1/2 md:left-[calc(50%+8rem)] -translate-x-1/2 z-20">
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

      {/* Input area - fixed at viewport bottom with sidebar offset */}
      <div className="fixed bottom-0 left-0 md:left-64 right-0 z-10 border-t bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="max-w-3xl mx-auto px-4 py-4">
          {renderComposer()}
        </div>
      </div>
    </div>
  );

  // Render composer (input area) - blocks.so polished styling
  const renderComposer = () => (
    <form 
      onSubmit={(e) => { e.preventDefault(); handleSend(); }}
      className="overflow-visible rounded-xl border p-2 transition-colors duration-200 focus-within:border-ring bg-card"
    >
      {/* Text input wrapper with fixed height */}
      <div className="min-h-[48px]">
        <Textarea
          ref={inputRef}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about your code..."
          disabled={isLoading}
          className={cn(
            'max-h-[200px] min-h-[48px] resize-none rounded-none border-none bg-transparent p-0 text-sm shadow-none',
            'focus-visible:outline-none focus-visible:ring-0 focus-visible:ring-offset-0',
            'placeholder:text-muted-foreground/60'
          )}
          rows={1}
        />
      </div>

      {/* Bottom toolbar */}
      <div className="flex items-center gap-1 pt-1">
        {/* Left side - action buttons */}
        <div className="flex items-center gap-0.5">
          {/* Plus dropdown for future features */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                className="h-7 w-7 rounded-md"
                size="icon"
                type="button"
                variant="ghost"
              >
                <Plus className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              align="start"
              className="w-48 rounded-xl p-1.5"
            >
              <DropdownMenuGroup className="space-y-1">
                <DropdownMenuItem className="rounded-lg text-xs cursor-pointer">
                  <Paperclip className="h-4 w-4 mr-2 text-muted-foreground" />
                  <span>Attach Files</span>
                </DropdownMenuItem>
                <DropdownMenuItem className="rounded-lg text-xs cursor-pointer">
                  <Link className="h-4 w-4 mr-2 text-muted-foreground" />
                  <span>Import from URL</span>
                </DropdownMenuItem>
                <DropdownMenuItem className="rounded-lg text-xs cursor-pointer">
                  <Clipboard className="h-4 w-4 mr-2 text-muted-foreground" />
                  <span>Paste from Clipboard</span>
                </DropdownMenuItem>
                <DropdownMenuItem className="rounded-lg text-xs cursor-pointer">
                  <FileText className="h-4 w-4 mr-2 text-muted-foreground" />
                  <span>Use Template</span>
                </DropdownMenuItem>
              </DropdownMenuGroup>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Settings dropdown for future features */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                className="h-7 w-7 rounded-md"
                size="icon"
                type="button"
                variant="ghost"
              >
                <Settings2 className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              align="start"
              className="w-48 rounded-xl p-1.5"
            >
              <DropdownMenuGroup className="space-y-1">
                <DropdownMenuItem className="rounded-lg text-xs cursor-pointer">
                  <Sparkles className="h-4 w-4 mr-2 text-muted-foreground" />
                  <span>Auto-complete</span>
                </DropdownMenuItem>
                <DropdownMenuItem className="rounded-lg text-xs cursor-pointer">
                  <Settings2 className="h-4 w-4 mr-2 text-muted-foreground" />
                  <span>Advanced Settings</span>
                </DropdownMenuItem>
              </DropdownMenuGroup>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Project selector */}
          {projects.length > 0 && (
            <div className="relative">
              <Select
                value={selectedProjectId || 'auto'}
                onValueChange={(value) => setSelectedProjectId(value === 'auto' ? null : value)}
              >
                <SelectTrigger className="h-7 w-auto min-w-[120px] max-w-[180px] rounded-md border-none bg-transparent text-xs relative z-0">
                  <SelectValue placeholder="Auto-detect" />
                </SelectTrigger>
                <SelectContent className="rounded-xl z-50">
                  <SelectItem value="auto" className="text-xs">
                    Auto-detect
                  </SelectItem>
                  {projects.map((project) => (
                    <SelectItem key={project.id} value={project.id} className="text-xs">
                      <div className="flex items-center gap-2">
                        <Github className="h-3 w-3 text-muted-foreground" />
                        <span>{project.name}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
        </div>

        {/* Right side - send button */}
        <div className="ml-auto flex items-center gap-1">
          <Button
            className="h-7 w-7 rounded-md"
            disabled={isLoading || !inputValue.trim()}
            size="icon"
            type="submit"
            variant="default"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <ArrowUp className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>
    </form>
  );

  return (
    <div className="flex flex-col h-full relative">
      {mode === 'empty' ? renderEmptyState() : renderTranscript()}
    </div>
  );
}
