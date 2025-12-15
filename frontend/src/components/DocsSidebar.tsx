import { Link, useLocation } from 'react-router-dom';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { useState } from 'react';
import { cn } from '@/lib/utils';
import { docsNav } from '@/data/docsStructure';

export default function DocsSidebar() {
  const location = useLocation();
  const [expandedSections, setExpandedSections] = useState<string[]>(
    // Expand all sections by default
    docsNav.map(section => section.title)
  );

  const toggleSection = (title: string) => {
    setExpandedSections(prev =>
      prev.includes(title)
        ? prev.filter(t => t !== title)
        : [...prev, title]
    );
  };

  const isActive = (path: string) => {
    return location.pathname === path;
  };

  return (
    <aside className="w-64 flex-shrink-0 border-r border-border bg-card overflow-y-auto">
      <div className="p-4">
        {/* Header */}
        <div className="mb-6">
          <h2 className="text-lg font-semibold text-foreground">Documentation</h2>
          <p className="text-xs text-muted-foreground mt-1">
            Learn how to use Sline
          </p>
        </div>

        {/* Navigation sections */}
        <nav className="space-y-1">
          {/* Home link */}
          <Link
            to="/docs"
            className={cn(
              'flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-md transition-colors',
              location.pathname === '/docs'
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
            )}
          >
            <span>📚</span>
            <span>Home</span>
          </Link>

          {/* Sections */}
          {docsNav.map((section) => {
            const Icon = section.icon;
            const isExpanded = expandedSections.includes(section.title);

            return (
              <div key={section.title} className="space-y-1">
                {/* Section header */}
                <button
                  onClick={() => toggleSection(section.title)}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm font-medium text-foreground hover:bg-accent rounded-md transition-colors"
                >
                  <Icon className="h-4 w-4 flex-shrink-0" />
                  <span className="flex-1 text-left">{section.title}</span>
                  {isExpanded ? (
                    <ChevronDown className="h-4 w-4" />
                  ) : (
                    <ChevronRight className="h-4 w-4" />
                  )}
                </button>

                {/* Section items */}
                {isExpanded && (
                  <div className="ml-6 space-y-1">
                    {section.items.map((item) => (
                      <Link
                        key={item.path}
                        to={item.path}
                        className={cn(
                          'block px-3 py-2 text-sm rounded-md transition-colors',
                          isActive(item.path)
                            ? 'bg-primary/10 text-primary font-medium'
                            : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                        )}
                      >
                        {item.title}
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </nav>
      </div>
    </aside>
  );
}
