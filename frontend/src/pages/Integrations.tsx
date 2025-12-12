import { useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, Circle, MessageSquare } from 'lucide-react';
import { SiSlack, SiDiscord, SiJira, SiAsana, SiGoogledrive, SiGithub, SiPostgresql, SiMongodb } from '@icons-pack/react-simple-icons';

interface Integration {
  name: string;
  description: string;
  icon: React.ComponentType<{ size?: number; color?: string; className?: string }>;
  color: string;
  status: 'connected' | 'available' | 'coming_soon';
  category: 'event' | 'mcp';
}

const integrations: Integration[] = [
  // Event Integrations
  {
    name: 'Slack',
    description: 'Interact with Sline directly from Slack channels',
    icon: SiSlack,
    color: '#4A154B',
    status: 'connected',
    category: 'event',
  },
  {
    name: 'Discord',
    description: 'Connect Sline to your Discord server',
    icon: SiDiscord,
    color: '#5865F2',
    status: 'coming_soon',
    category: 'event',
  },
  {
    name: 'Microsoft Teams',
    description: 'Integrate with Microsoft Teams for enterprise workflows',
    icon: MessageSquare,
    color: '#6264A7',
    status: 'coming_soon',
    category: 'event',
  },
  // MCP Servers (Downstream Integrations)
  {
    name: 'Jira',
    description: 'Access and manage Jira issues, projects, and workflows',
    icon: SiJira,
    color: '#0052CC',
    status: 'available',
    category: 'mcp',
  },
  {
    name: 'Asana',
    description: 'Connect to Asana for task and project management',
    icon: SiAsana,
    color: '#F06A6A',
    status: 'available',
    category: 'mcp',
  },
  {
    name: 'Google Drive',
    description: 'Read and write files in Google Drive',
    icon: SiGoogledrive,
    color: '#4285F4',
    status: 'available',
    category: 'mcp',
  },
  {
    name: 'GitHub',
    description: 'Advanced GitHub operations, issues, PRs, and repository management',
    icon: SiGithub,
    color: '#181717',
    status: 'available',
    category: 'mcp',
  },
  {
    name: 'PostgreSQL',
    description: 'Query and manage PostgreSQL databases',
    icon: SiPostgresql,
    color: '#4169E1',
    status: 'available',
    category: 'mcp',
  },
  {
    name: 'MongoDB',
    description: 'Connect to MongoDB databases for document operations',
    icon: SiMongodb,
    color: '#47A248',
    status: 'available',
    category: 'mcp',
  },
];

export default function Integrations() {
  const mcpServersRef = useRef<HTMLDivElement>(null);
  const location = useLocation();

  // Scroll to MCP Servers section if navigated from Settings
  const scrollToMcpServers = () => {
    mcpServersRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  // Auto-scroll if coming from settings
  if (location.state?.scrollTo === 'mcp-servers') {
    setTimeout(scrollToMcpServers, 100);
  }

  const eventIntegrations = integrations.filter((i) => i.category === 'event');
  const mcpIntegrations = integrations.filter((i) => i.category === 'mcp');

  const getStatusBadge = (status: Integration['status']) => {
    switch (status) {
      case 'connected':
        return (
          <Badge className="bg-green-500 text-white hover:bg-green-600">
            <CheckCircle2 className="h-3 w-3 mr-1" />
            Connected
          </Badge>
        );
      case 'available':
        return (
          <Badge variant="secondary">
            Available
          </Badge>
        );
      case 'coming_soon':
        return (
          <Badge variant="outline" className="border-dashed">
            <Circle className="h-3 w-3 mr-1" />
            Coming Soon
          </Badge>
        );
    }
  };

  return (
    <div className="space-y-8 max-w-7xl">
      {/* Event Integrations */}
      <section>
        <div className="mb-4">
          <h3 className="text-xl font-semibold text-foreground">Event Integrations</h3>
          <p className="text-sm text-muted-foreground mt-1">
            Chat platforms and communication tools where you can interact with Sline
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {eventIntegrations.map((integration) => {
            const Icon = integration.icon;
            return (
              <Card
                key={integration.name}
                className={`transition-all hover:shadow-lg ${
                  integration.status === 'coming_soon'
                    ? 'opacity-60 cursor-not-allowed'
                    : 'hover:border-primary/50 cursor-pointer'
                }`}
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div
                        className="p-2 rounded-lg bg-muted border border-border"
                      >
                        <Icon size={24} color={integration.color} className="opacity-90" />
                      </div>
                      <div>
                        <CardTitle className="text-base">{integration.name}</CardTitle>
                      </div>
                    </div>
                    {getStatusBadge(integration.status)}
                  </div>
                  <CardDescription className="mt-2">
                    {integration.description}
                  </CardDescription>
                </CardHeader>
              </Card>
            );
          })}
        </div>
      </section>

      {/* Downstream Integrations (MCP Servers) */}
      <section ref={mcpServersRef} id="mcp-servers">
        <div className="mb-4">
          <h3 className="text-xl font-semibold text-foreground">
            Downstream Integrations (MCP Servers)
          </h3>
          <p className="text-sm text-muted-foreground mt-1">
            Extend Sline's capabilities with Model Context Protocol servers for external tools and services
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {mcpIntegrations.map((integration) => {
            const Icon = integration.icon;
            return (
              <Card
                key={integration.name}
                className="transition-all hover:shadow-lg hover:border-primary/50 cursor-pointer"
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div
                        className="p-2 rounded-lg bg-muted border border-border"
                      >
                        <Icon size={24} color={integration.color} className="opacity-90" />
                      </div>
                      <div>
                        <CardTitle className="text-base">{integration.name}</CardTitle>
                      </div>
                    </div>
                    {getStatusBadge(integration.status)}
                  </div>
                  <CardDescription className="mt-2">
                    {integration.description}
                  </CardDescription>
                </CardHeader>
              </Card>
            );
          })}
        </div>
      </section>

      {/* Info Section */}
      <Card className="bg-muted/50">
        <CardHeader>
          <CardTitle className="text-lg">Getting Started with Integrations</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <div>
            <p className="font-medium text-foreground mb-1">Event Integrations</p>
            <p>
              Event integrations allow you to interact with Sline from your preferred communication platform.
              Simply @mention Sline in Slack to get started!
            </p>
          </div>
          <div>
            <p className="font-medium text-foreground mb-1">MCP Servers</p>
            <p>
              Model Context Protocol (MCP) servers extend Sline's capabilities by providing access to
              external APIs and services. Configure MCP servers in{' '}
              <a href="/settings" className="text-primary hover:underline">
                Settings
              </a>{' '}
              to enable these integrations.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
