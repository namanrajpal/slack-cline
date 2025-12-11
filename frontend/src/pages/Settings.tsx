import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import ProvidersTab from './settings/ProvidersTab';
import AgentTab from './settings/AgentTab';
import RulesTab from './settings/RulesTab';
import McpServersTab from './settings/McpServersTab';
import AdvancedTab from './settings/AdvancedTab';

export default function Settings() {
  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h2 className="text-2xl font-bold text-foreground">Settings</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Configure your coding agent, API providers, and workflows
        </p>
      </div>

      <Tabs defaultValue="providers" className="space-y-6">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="providers">Providers</TabsTrigger>
          <TabsTrigger value="agent">Agent</TabsTrigger>
          <TabsTrigger value="rules">Rules & Workflows</TabsTrigger>
          <TabsTrigger value="mcp">MCP Servers</TabsTrigger>
          <TabsTrigger value="advanced">Advanced</TabsTrigger>
        </TabsList>

        <TabsContent value="providers">
          <ProvidersTab />
        </TabsContent>

        <TabsContent value="agent">
          <AgentTab />
        </TabsContent>

        <TabsContent value="rules">
          <RulesTab />
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
