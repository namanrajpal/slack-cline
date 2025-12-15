/**
 * ChatPanel - Main chat interface for Dashboard.
 * 
 * Custom chat component using shadcn/ui with SSE streaming support.
 */

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { useChatStream } from '@/hooks/useChatStream';
import { useAutoScroll } from '@/hooks/useAutoScroll';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { Bot } from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';

interface ChatPanelProps {
  className?: string;
}

export function ChatPanel({ className }: ChatPanelProps) {
  const { toast } = useToast();

  // Auto-scroll hook (only scrolls when near bottom)
  const {
    containerRef,
    endRef: messagesEndRef,
    isAtBottom,
    scrollToBottom,
    onScroll,
    resetUserScroll,
  } = useAutoScroll({ thresholdPx: 100 });

  const { messages, isLoading, sendMessage } = useChatStream({
    onError: (error) => {
      toast({
        title: 'Chat Error',
        description: error.message,
        variant: 'destructive',
      });
    },
  });

  // Handle send with scroll reset
  const handleSend = async (text: string) => {
    resetUserScroll();
    scrollToBottom('instant');
    await sendMessage(text);
  };

  return (
    <Card className={`flex flex-col ${className}`}>
      <CardHeader className="flex-shrink-0 space-y-1">
        <div className="flex items-center gap-2">
          <Bot className="h-5 w-5 text-primary" />
          <CardTitle className="text-xl">Sline AI Assistant</CardTitle>
        </div>
        <CardDescription>
          Ask me anything about your codebase. I can help you understand, refactor, or debug your code.
        </CardDescription>
      </CardHeader>
      
      <Separator />
      
      <CardContent className="flex flex-col flex-1 min-h-0 p-0">
        {/* Messages Area */}
        <div
          ref={containerRef}
          onScroll={onScroll}
          className="flex-1 overflow-y-auto p-4 space-y-4"
        >
          {messages.length === 0 ? (
            <div className="flex items-center justify-center h-full text-center text-muted-foreground">
              <div className="space-y-2 max-w-md">
                <Bot className="h-12 w-12 mx-auto opacity-50" />
                <p className="text-sm">
                  Start a conversation by asking about your code. Try questions like:
                </p>
                <ul className="text-xs space-y-1">
                  <li>"What does this project do?"</li>
                  <li>"Show me the main components"</li>
                  <li>"Help me refactor this function"</li>
                </ul>
              </div>
            </div>
          ) : (
            <>
              {messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>
        
        <Separator />
        
        {/* Input Area */}
        <div className="flex-shrink-0 p-4 bg-muted/30">
          <ChatInput
            onSend={handleSend}
            disabled={isLoading}
            placeholder="Ask about your code..."
          />
        </div>
      </CardContent>
    </Card>
  );
}
