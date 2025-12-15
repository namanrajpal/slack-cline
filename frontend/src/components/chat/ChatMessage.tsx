/**
 * ChatMessage - Individual message bubble component.
 * 
 * Displays user or assistant messages with markdown rendering and tool calls.
 * Tool calls are collapsible ChatGPT-style.
 */

import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import MarkdownRenderer from '@/components/MarkdownRenderer';
import { 
  Wrench, 
  Check, 
  Loader2, 
  ChevronDown, 
  ChevronRight,
  FileText,
  FolderOpen,
  Search
} from 'lucide-react';
import type { ChatMessage as ChatMessageType, ToolCall } from '@/hooks/useChatStream';
import { cn } from '@/lib/utils';

interface ChatMessageProps {
  message: ChatMessageType;
}

// Get appropriate icon for tool
function getToolIcon(toolName: string) {
  switch (toolName) {
    case 'read_file':
      return FileText;
    case 'list_files':
      return FolderOpen;
    case 'search_files':
      return Search;
    default:
      return Wrench;
  }
}

// Truncate result for display
function truncateResult(result: string | undefined, maxLength = 200): string {
  if (!result) return '';
  // Clean up the result string (it's often a stringified object)
  const cleaned = result.replace(/^content=["']|["']$/g, '').slice(0, maxLength);
  return cleaned.length < result.length ? cleaned + '...' : cleaned;
}

// Tool calls section component
function ToolCallsSection({ toolCalls }: { toolCalls: ToolCall[] }) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  // Check if all tools are done
  const allDone = toolCalls.every((t) => t.status === 'complete');
  const pendingCount = toolCalls.filter((t) => t.status === 'pending').length;
  
  return (
    <div className="mb-3">
      {/* Collapsed header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={cn(
          "flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors",
          "w-full text-left py-1"
        )}
      >
        {isExpanded ? (
          <ChevronDown className="h-4 w-4" />
        ) : (
          <ChevronRight className="h-4 w-4" />
        )}
        
        {allDone ? (
          <span className="flex items-center gap-1.5">
            <Check className="h-3.5 w-3.5 text-green-500" />
            Used {toolCalls.length} tool{toolCalls.length > 1 ? 's' : ''}
          </span>
        ) : (
          <span className="flex items-center gap-1.5">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Running {pendingCount} of {toolCalls.length} tools...
          </span>
        )}
        
        {/* Tool name badges in collapsed view */}
        {!isExpanded && (
          <div className="flex flex-wrap gap-1 ml-2">
            {toolCalls.map((tool) => {
              const Icon = getToolIcon(tool.name);
              return (
                <Badge
                  key={tool.id}
                  variant="outline"
                  className="text-xs py-0 px-1.5"
                >
                  <Icon className="h-3 w-3 mr-1" />
                  {tool.name}
                </Badge>
              );
            })}
          </div>
        )}
      </button>
      
      {/* Expanded details */}
      {isExpanded && (
        <div className="mt-2 space-y-2 pl-6 border-l-2 border-muted ml-2">
          {toolCalls.map((tool) => {
            const Icon = getToolIcon(tool.name);
            return (
              <div
                key={tool.id}
                className="text-sm bg-muted/50 rounded-md p-2"
              >
                <div className="flex items-center gap-2 font-medium">
                  <Icon className="h-4 w-4" />
                  <span>{tool.name}</span>
                  {tool.args && (
                    <code className="text-xs bg-muted px-1.5 py-0.5 rounded">
                      {tool.args}
                    </code>
                  )}
                  {tool.status === 'pending' ? (
                    <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
                  ) : (
                    <Check className="h-3 w-3 text-green-500" />
                  )}
                </div>
                
                {tool.result && tool.status === 'complete' && (
                  <div className="mt-1.5 text-xs text-muted-foreground font-mono whitespace-pre-wrap break-all">
                    {truncateResult(tool.result, 300)}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const hasToolCalls = message.toolCalls && message.toolCalls.length > 0;

  return (
    <div
      className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'} mb-4`}
    >
      <div className={`max-w-[85%] ${isUser ? 'items-end' : 'items-start'} flex flex-col`}>
        {/* Tool calls - positioned ABOVE content for assistant messages */}
        {!isUser && hasToolCalls && (
          <ToolCallsSection toolCalls={message.toolCalls!} />
        )}
        
        {/* Message content */}
        {isUser ? (
          // User messages in a card/bubble
          <Card className="p-4 bg-primary text-primary-foreground">
            <p className="whitespace-pre-wrap">{message.content}</p>
          </Card>
        ) : (
          // Assistant messages as plain text (ChatGPT style)
          <div className="prose prose-sm dark:prose-invert max-w-none text-foreground">
            {message.content ? (
              <MarkdownRenderer content={message.content} />
            ) : hasToolCalls ? (
              // Show nothing if tools are running (the ToolCallsSection shows status)
              null
            ) : (
              <span className="text-muted-foreground italic">Thinking...</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
