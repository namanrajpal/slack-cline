import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import rehypeRaw from 'rehype-raw';
import { Link } from 'react-router-dom';
import 'highlight.js/styles/github-dark.css';

interface MarkdownRendererProps {
  content: string;
}

export default function MarkdownRenderer({ content }: MarkdownRendererProps) {
  return (
    <div className="markdown-content prose prose-slate dark:prose-invert max-w-none">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight, rehypeRaw]}
        components={{
          // Custom link handling for internal docs links
          a: ({ node, href, children, ...props }) => {
            // Handle relative markdown links (e.g., "getting-started/quickstart.md")
            if (href?.endsWith('.md')) {
              const docsPath = `/docs/${href.replace('.md', '')}`;
              return (
                <Link to={docsPath} className="text-primary hover:underline">
                  {children}
                </Link>
              );
            }
            
            // Handle already-formatted /docs links
            if (href?.startsWith('/docs')) {
              return (
                <Link to={href} className="text-primary hover:underline">
                  {children}
                </Link>
              );
            }
            
            // Handle internal links starting with ../
            if (href?.startsWith('../')) {
              // External link (goes up to root README.md)
              return (
                <a
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:underline"
                  {...props}
                >
                  {children}
                </a>
              );
            }
            
            // External links open in new tab
            return (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline"
                {...props}
              >
                {children}
              </a>
            );
          },
          // Transform image paths to use public directory
          img: ({ node, src, alt, ...props }) => {
            let imageSrc = src;
            
            // Handle relative paths to docs images
            if (src && !src.startsWith('http') && !src.startsWith('/')) {
              // Transform relative paths like "sline-architecture.png" to "/docs/sline-architecture.png"
              imageSrc = `/docs/${src.split('/').pop()}`;
            }
            
            return (
              <img
                src={imageSrc}
                alt={alt}
                className="rounded-lg border border-border shadow-sm my-4"
                {...props}
              />
            );
          },
          // Style code blocks
          code: ({ node, className, children, ...props }) => {
            const match = /language-(\w+)/.exec(className || '');
            const isInline = !match;
            
            if (isInline) {
              return (
                <code
                  className="px-1.5 py-0.5 rounded bg-muted text-sm font-mono"
                  {...props}
                >
                  {children}
                </code>
              );
            }
            
            return (
              <code className={className} {...props}>
                {children}
              </code>
            );
          },
          // Style tables
          table: ({ node, ...props }) => (
            <div className="overflow-x-auto my-4">
              <table className="min-w-full divide-y divide-border" {...props} />
            </div>
          ),
          th: ({ node, ...props }) => (
            <th
              className="px-4 py-2 text-left text-sm font-semibold bg-muted"
              {...props}
            />
          ),
          td: ({ node, ...props }) => (
            <td className="px-4 py-2 text-sm border-t border-border" {...props} />
          ),
          // Style blockquotes
          blockquote: ({ node, ...props }) => (
            <blockquote
              className="border-l-4 border-primary pl-4 py-2 my-4 italic text-muted-foreground"
              {...props}
            />
          ),
          // Style headings
          h1: ({ node, ...props }) => (
            <h1 className="text-4xl font-bold mt-8 mb-4" {...props} />
          ),
          h2: ({ node, ...props }) => (
            <h2 className="text-3xl font-semibold mt-6 mb-3" {...props} />
          ),
          h3: ({ node, ...props }) => (
            <h3 className="text-2xl font-semibold mt-5 mb-2" {...props} />
          ),
          h4: ({ node, ...props }) => (
            <h4 className="text-xl font-semibold mt-4 mb-2" {...props} />
          ),
          // Style lists
          ul: ({ node, ...props }) => (
            <ul className="list-disc list-inside my-4 space-y-1" {...props} />
          ),
          ol: ({ node, ...props }) => (
            <ol className="list-decimal list-inside my-4 space-y-1" {...props} />
          ),
          // Style paragraphs
          p: ({ node, ...props }) => (
            <p className="my-4 leading-7" {...props} />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
