import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, FolderGit2, Settings, Puzzle } from 'lucide-react';
import { cn } from '@/lib/utils';
import ThemeSwitcher from './ThemeSwitcher';

export default function Sidebar() {
  const location = useLocation();

  const isActive = (path: string) => {
    return location.pathname === path || location.pathname.startsWith(path + '/');
  };

  const navItems = [
    { path: '/', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/projects', label: 'Projects', icon: FolderGit2 },
    { path: '/integrations', label: 'Integrations', icon: Puzzle },
    { path: '/settings', label: 'Settings', icon: Settings },
  ];

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
        <nav className="flex-1 px-2 space-y-1">
          {navItems.map((item) => {
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
