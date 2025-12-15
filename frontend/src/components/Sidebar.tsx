import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, FolderGit2, Settings, Puzzle, BookOpen, MessageSquare, Plus, ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import ThemeSwitcher from './ThemeSwitcher';
import { useConversations } from '@/hooks/useConversations';
import { useState } from 'react';

export default function Sidebar() {
  const location = useLocation();
  const [chatExpanded, setChatExpanded] = useState(true);
  const { conversations, isLoading: conversationsLoading } = useConversations({ limit: 10 });

  const isActive = (path: string) => {
    return location.pathname === path || location.pathname.startsWith(path + '/');
  };

  const isChatActive = location.pathname.startsWith('/chat');

  const navItems = [
    { path: '/', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/projects', label: 'Projects', icon: FolderGit2 },
    { path: '/integrations', label: 'Integrations', icon: Puzzle },
    { path: '/docs', label: 'Documentation', icon: BookOpen },
    { path: '/settings', label: 'Settings', icon: Settings },
  ];

  // Format relative time
  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);
    
    if (diffInSeconds < 60) return 'now';
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h`;
    if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)}d`;
    return `${Math.floor(diffInSeconds / 604800)}w`;
  };

  return (
    <aside className="hidden md:flex md:w-64 md:flex-col md:fixed md:inset-y-0">
      <div className="flex flex-col flex-grow border-r border-border bg-card pt-5 pb-4 overflow-y-auto">
        {/* Logo/Brand */}
        <div className="flex items-center flex-shrink-0 px-4 mb-5">
          <Link to="/" className="flex items-center gap-3">
            <img 
              src="/sline-logo.png" 
              alt="Sline" 
              className="h-8 w-8"
            />
            <div className="text-xl font-bold text-foreground">
              Sline
            </div>
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-2 space-y-1 overflow-y-auto">
          {/* Dashboard */}
          <Link
            to="/"
            className={cn(
              'group flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors',
              location.pathname === '/'
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
            )}
          >
            <LayoutDashboard
              className={cn(
                'mr-3 h-5 w-5 flex-shrink-0',
                location.pathname === '/' ? 'text-primary-foreground' : 'text-muted-foreground group-hover:text-accent-foreground'
              )}
            />
            Dashboard
          </Link>

          {/* Chat Section */}
          <div className="space-y-1">
            {/* Chat Header with Toggle */}
            <div
              className={cn(
                'group flex items-center justify-between px-3 py-2 text-sm font-medium rounded-md transition-colors cursor-pointer',
                isChatActive
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
              )}
              onClick={() => setChatExpanded(!chatExpanded)}
            >
              <Link to="/chat" className="flex items-center flex-1" onClick={(e) => e.stopPropagation()}>
                <MessageSquare
                  className={cn(
                    'mr-3 h-5 w-5 flex-shrink-0',
                    isChatActive ? 'text-primary-foreground' : 'text-muted-foreground group-hover:text-accent-foreground'
                  )}
                />
                Chat
              </Link>
              <div className="flex items-center gap-1">
                <Link
                  to="/chat"
                  onClick={(e) => e.stopPropagation()}
                  className={cn(
                    'p-1 rounded hover:bg-primary-foreground/20',
                    isChatActive ? 'text-primary-foreground' : 'text-muted-foreground'
                  )}
                  title="New chat"
                >
                  <Plus className="h-4 w-4" />
                </Link>
                {chatExpanded ? (
                  <ChevronDown className={cn('h-4 w-4', isChatActive ? 'text-primary-foreground' : 'text-muted-foreground')} />
                ) : (
                  <ChevronRight className={cn('h-4 w-4', isChatActive ? 'text-primary-foreground' : 'text-muted-foreground')} />
                )}
              </div>
            </div>

            {/* Conversation List */}
            {chatExpanded && (
              <div className="ml-4 space-y-0.5">
                {conversationsLoading ? (
                  <div className="px-3 py-2 text-xs text-muted-foreground">Loading...</div>
                ) : conversations.length === 0 ? (
                  <div className="px-3 py-2 text-xs text-muted-foreground">No conversations yet</div>
                ) : (
                  conversations.map((conv) => {
                    const isConvActive = location.pathname === `/chat/${conv.threadId}`;
                    return (
                      <Link
                        key={conv.threadId}
                        to={`/chat/${conv.threadId}`}
                        className={cn(
                          'group flex items-center px-3 py-1.5 text-xs rounded-md transition-colors',
                          isConvActive
                            ? 'bg-accent text-accent-foreground'
                            : 'text-muted-foreground hover:bg-accent/50 hover:text-accent-foreground'
                        )}
                        title={conv.title}
                      >
                        <span className="truncate flex-1">{conv.title}</span>
                        <span className="ml-2 text-[10px] opacity-60 flex-shrink-0">
                          {formatTimeAgo(conv.updatedAt)}
                        </span>
                      </Link>
                    );
                  })
                )}
              </div>
            )}
          </div>

          {/* Other Nav Items */}
          {navItems.slice(1).map((item) => {
            const Icon = item.icon;
            const active = isActive(item.path);
            
            return (
              <Link
                key={item.path}
                to={item.path}
                className={cn(
                  'group flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors',
                  active
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                )}
              >
                <Icon
                  className={cn(
                    'mr-3 h-5 w-5 flex-shrink-0',
                    active ? 'text-primary-foreground' : 'text-muted-foreground group-hover:text-accent-foreground'
                  )}
                />
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="flex-shrink-0 border-t border-border">
          <div className="flex items-center justify-between p-4">
            <div>
              <p className="text-xs font-medium text-foreground">Sline Agent</p>
              <p className="text-xs text-muted-foreground">Coding teammate</p>
            </div>
          </div>
          <div className="px-2 pb-3">
            <ThemeSwitcher />
          </div>
        </div>
      </div>
    </aside>
  );
}
