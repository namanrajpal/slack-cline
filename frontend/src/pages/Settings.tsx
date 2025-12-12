import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import ProvidersTab from './settings/ProvidersTab';
import AgentTab from './settings/AgentTab';
import McpServersTab from './settings/McpServersTab';
import AdvancedTab from './settings/AdvancedTab';

export default function Settings() {
  return (
    <div className="space-y-6 max-w-5xl">
      <Tabs defaultValue="providers" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="providers">Providers</TabsTrigger>
          <TabsTrigger value="agent">Agent</TabsTrigger>
          <TabsTrigger value="mcp">MCP Servers</TabsTrigger>
          <TabsTrigger value="advanced">Advanced</TabsTrigger>
        </TabsList>

        <TabsContent value="providers">
          <ProvidersTab />
        </TabsContent>

        <TabsContent value="agent">
          <AgentTab />
        </TabsContent>

        <TabsContent value="mcp">
          <McpServersTab />
        </TabsContent>

        <TabsContent value="advanced">
          <AdvancedTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
