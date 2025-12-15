import { useParams } from 'react-router-dom';
import DocsSidebar from '@/components/DocsSidebar';
import MarkdownRenderer from '@/components/MarkdownRenderer';
import { getDocContent } from '@/utils/docsLoader';
import { allDocs } from '@/data/docsStructure';
import { AlertCircle } from 'lucide-react';

export default function Docs() {
  const { '*': slug } = useParams();
  
  // If no slug, show home (README)
  const contentSlug = slug || 'index';
  
  // Get markdown content
  const content = getDocContent(contentSlug);
  
  // Get doc info for title
  const docInfo = allDocs.find(doc => doc.slug === contentSlug);
  
  if (!content) {
    return (
      <div className="flex h-screen">
        <DocsSidebar />
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-4xl mx-auto py-12 px-6">
            <div className="flex items-center gap-3 p-4 border border-destructive/50 rounded-lg bg-destructive/10">
              <AlertCircle className="h-5 w-5 text-destructive" />
              <div>
                <h3 className="font-semibold text-destructive">Page Not Found</h3>
                <p className="text-sm text-muted-foreground">
                  The documentation page you're looking for doesn't exist.
                </p>
              </div>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <DocsSidebar />
      
      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto py-8 px-6">
          {/* Breadcrumb or title */}
          {docInfo && (
            <div className="mb-6">
              <p className="text-sm text-muted-foreground mb-1">
                {slug ? slug.split('/').join(' / ') : 'Home'}
              </p>
              <h1 className="text-3xl font-bold text-foreground">
                {docInfo.title}
              </h1>
            </div>
          )}
          
          {/* Markdown content */}
          <MarkdownRenderer content={content} />
          
          {/* Footer */}
          <div className="mt-12 pt-6 border-t border-border">
            <p className="text-sm text-muted-foreground">
              Found an issue with the docs?{' '}
              <a
                href="https://github.com/your-org/sline/issues"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline"
              >
                Report it on GitHub
              </a>
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
