# Implementation Plan

## [Overview]

Transform the existing Vite + React + Tailwind frontend into a GitHub-style settings dashboard with shadcn/ui components and a custom color palette.

The current frontend has a basic top-navigation layout with simple pages for Dashboard, Projects, Runs, and Settings. The Settings page only handles API key configuration through a single form. This implementation will completely redesign the UI to provide a professional, calm, developer-focused experience similar to GitHub's settings pages.

The transformation includes: (1) integrating shadcn/ui component library with proper theming, (2) implementing a custom color palette across Tailwind and CSS variables, (3) replacing the top navigation with a left sidebar layout, (4) completely rebuilding the Settings page as a tabbed interface with five sections (Providers, Agent, Rules & Workflows, MCP Servers, Advanced), and (5) creating reusable components that follow GitHub's visual language of cards, forms, and subtle accents.

The existing API client structure and TypeScript types will be preserved and extended. Backend integration points will be clearly marked with TODO comments where endpoints don't yet exist, making it easy to wire up functionality later. The design prioritizes calm neutrals with strategic accent colors, generous spacing, and responsive behavior that adapts from desktop sidebar to mobile navigation.

## [Backend Compatibility]

Alignment with existing backend schemas and identification of features that work NOW vs. need backend development.

**Current Backend API Endpoints (Work NOW)**:

1. **Projects API** (`/api/projects`):
   - GET `/api/projects` - List all projects
   - POST `/api/projects` - Create project
   - PUT `/api/projects/{id}` - Update project
   - DELETE `/api/projects/{id}` - Delete project
   - Backend schema: `ProjectResponseSchema` with fields: `id`, `tenant_id`, `name`, `description`, `slack_channel_id`, `repo_url`, `default_ref`, `created_at`, `updated_at`

2. **Runs API** (`/api/runs`):
   - GET `/api/runs` - List runs with filters
   - GET `/api/runs/{id}` - Get run details
   - POST `/api/runs/{id}/respond` - Approve/deny run
   - Backend schema: `RunResponseSchema` - fully aligned with frontend

3. **API Config** (`/api/config/api-keys`):
   - GET `/api/config/api-keys` - Get current config (API key masked)
   - POST `/api/config/api-keys` - Update config (requires backend restart)
   - Backend schema: `ApiKeyConfigSchema` with fields: `provider`, `api_key`, `model_id`, `base_url`

**Features Needing Backend Endpoints (TODO)**:

1. **Agent Configuration** - Not yet implemented
   - Needed: GET/POST `/api/config/agent`
   - Fields: persona, autonomy settings, defaults

2. **Rules & Workflows** - Not yet implemented
   - Needed: CRUD endpoints for `/api/config/rules`
   - Fields: rule type, source, content, sync functionality

3. **MCP Servers** - Not yet implemented
   - Needed: CRUD endpoints for `/api/mcp-servers`
   - Fields: name, type, endpoint, auth, status testing

4. **Test Connection** - Not yet implemented
   - Needed: POST `/api/config/api-keys/test`
   - Returns: connection success, model info, latency

**Implementation Strategy**:

- **ProvidersTab**: Fully functional NOW with existing API
- **Other tabs**: Implement with mock/stub data, clear TODO markers for backend integration
- **Progressive enhancement**: Backend endpoints can be added incrementally without breaking UI

## [Types]

Extend the existing TypeScript type definitions to support new configuration models and fix alignment with backend schemas.

**Types to Modify** (in `frontend/src/types/index.ts`):

```typescript
// FIX: Update Project type to match backend ProjectResponseSchema
export interface Project {
  id: string;
  tenant_id: string;
  name: string;                    // ADD: Project name (required in backend)
  description?: string;            // ADD: Project description (optional)
  slack_channel_id: string;        // CHANGE: Make required (was optional)
  repo_url: string;
  default_ref: string;
  created_at: string;
  updated_at: string;
}

// FIX: Update ProjectCreate to match backend ProjectCreateSchema
export interface ProjectCreate {
  tenant_id?: string;              // Keep optional (defaults to "default")
  name: string;                    // ADD: Required project name
  description?: string;            // ADD: Optional description
  slack_channel_id?: string;       // Keep optional
  repo_url: string;
  default_ref?: string;            // Keep optional (defaults to "main")
}
```

**New Types to Add** (in `frontend/src/types/index.ts`):

```typescript
// Agent configuration types
export interface AgentConfig {
  persona: string; // System prompt / agent persona
  allow_file_writes: boolean;
  allow_shell_commands: boolean;
  require_approval_for_large_plans: boolean;
  default_project?: string;
  max_concurrent_tasks: number;
  temperature?: number;
  max_tokens?: number;
}

// Rules and workflows types
export interface RuleConfig {
  id: string;
  type: 'cline' | 'cursor' | 'claude_skills' | 'agent_md';
  name: string;
  source_type: 'file' | 'repo' | 'inline';
  source_location: string; // File path, repo URL, or inline content
  content?: string;
  last_synced_at?: string;
  enabled: boolean;
}

// MCP Server types
export interface McpServer {
  id: string;
  name: string;
  type: 'filesystem' | 'git' | 'http' | 'database' | 'custom';
  endpoint: string;
  status: 'connected' | 'error' | 'disabled';
  auth_method: 'none' | 'api_key' | 'oauth' | 'basic';
  auth_config?: Record<string, string>;
  created_at: string;
  updated_at: string;
}

export interface McpServerCreate {
  name: string;
  type: string;
  endpoint: string;
  auth_method: string;
  auth_config?: Record<string, string>;
}

// Enhanced provider config (extends existing ApiKeyConfig)
export interface ProviderConfig extends ApiKeyConfig {
  temperature?: number;
  max_tokens?: number;
  custom_headers?: Record<string, string>;
}

// Form state types for Settings tabs
export interface SettingsTabProps {
  // Common interface for all settings tab components
}
```

**Notes on Type Alignment**:

- `ApiKeyConfig` - Perfectly aligned with backend `ApiKeyConfigSchema`, no changes needed
- `Run` and `RunFilters` - Already aligned with backend schemas
- `TestSlackRequest` and `TestSlackResponse` - Aligned with backend test endpoints
- `Project` types need updates to match backend's addition of `name` and `description` fields
- New types (Agent, Rules, MCP) are additive and prepared for future backend endpoints

## [Files]

Comprehensive file changes organized by category.

**New Files to Create**:

1. **shadcn/ui Setup Files**:
   - `frontend/src/lib/utils.ts` - shadcn's `cn()` utility function for class merging
   - `frontend/src/components/ui/button.tsx` - Button component
   - `frontend/src/components/ui/card.tsx` - Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter
   - `frontend/src/components/ui/input.tsx` - Input component
   - `frontend/src/components/ui/label.tsx` - Label component
   - `frontend/src/components/ui/textarea.tsx` - Textarea component
   - `frontend/src/components/ui/switch.tsx` - Switch/toggle component
   - `frontend/src/components/ui/select.tsx` - Select dropdown component
   - `frontend/src/components/ui/tabs.tsx` - Tabs, TabsList, TabsTrigger, TabsContent
   - `frontend/src/components/ui/dialog.tsx` - Dialog modal component
   - `frontend/src/components/ui/separator.tsx` - Separator/divider component
   - `frontend/src/components/ui/badge.tsx` - Badge component
   - `frontend/src/components/ui/toast.tsx` - Toast notification primitives
   - `frontend/src/components/ui/toaster.tsx` - Toast container component
   - `frontend/src/components/ui/use-toast.ts` - useToast hook

2. **Settings Tab Components** (in `frontend/src/pages/settings/`):
   - `ProvidersTab.tsx` - LLM provider and API key configuration
   - `AgentTab.tsx` - Agent behavior, persona, and autonomy settings
   - `RulesTab.tsx` - Cline rules, Cursor rules, Claude skills management
   - `McpServersTab.tsx` - MCP server listing and management
   - `AdvancedTab.tsx` - Placeholder for future advanced settings

3. **New Component Files**:
   - `frontend/src/components/Sidebar.tsx` - Left sidebar navigation component
   - `frontend/src/components/AppShell.tsx` - Main layout shell (sidebar + content area)

4. **Configuration Files**:
   - `frontend/components.json` - shadcn/ui configuration file

**Files to Modify**:

1. **`frontend/tailwind.config.js`**:
   - Add custom color palette to `theme.extend.colors`
   - Configure shadcn/ui theme variables
   - Add custom spacing, border radius, and other design tokens

2. **`frontend/src/index.css`**:
   - Add CSS custom properties for shadcn/ui theme (light/dark mode support)
   - Define color variables for the custom palette
   - Add base styles for shadcn components

3. **`frontend/package.json`**:
   - Add new dependencies (shadcn/ui related packages)

4. **`frontend/src/components/Layout.tsx`**:
   - Replace with new AppShell component that uses sidebar navigation
   - Remove top navigation bar styling
   - Integrate new responsive layout structure

5. **`frontend/src/pages/Settings.tsx`**:
   - Complete rewrite to use shadcn Tabs component
   - Import and render all five tab components
   - Remove existing form-based implementation

6. **`frontend/src/types/index.ts`**:
   - Add new type definitions listed in Types section

7. **`frontend/src/api/client.ts`**:
   - Add new methods for agent config, rules, and MCP servers
   - Mark with TODO comments for backend endpoints that don't exist yet

8. **`frontend/src/App.tsx`**:
   - Update to use new AppShell component instead of Layout
   - Ensure Settings route remains functional

9. **`frontend/tsconfig.json`**:
   - Add path alias for `@/` pointing to `src/` (shadcn convention)

**Files to Delete**:

None. All existing files will be preserved and modified as needed.

## [Functions]

New functions and API methods to support the enhanced settings dashboard.

**New API Client Methods** (in `frontend/src/api/client.ts`):

```typescript
// Agent Configuration
async getAgentConfig(): Promise<AgentConfig> {
  // TODO: Backend endpoint /api/config/agent
  const response = await api.get<AgentConfig>('/api/config/agent');
  return response.data;
}

async updateAgentConfig(config: AgentConfig): Promise<{ success: boolean; message: string }> {
  // TODO: Backend endpoint /api/config/agent
  const response = await api.post('/api/config/agent', config);
  return response.data;
}

// Rules & Workflows
async getRules(): Promise<RuleConfig[]> {
  // TODO: Backend endpoint /api/config/rules
  const response = await api.get<RuleConfig[]>('/api/config/rules');
  return response.data;
}

async createRule(rule: Omit<RuleConfig, 'id'>): Promise<RuleConfig> {
  // TODO: Backend endpoint /api/config/rules
  const response = await api.post<RuleConfig>('/api/config/rules', rule);
  return response.data;
}

async updateRule(id: string, rule: Partial<RuleConfig>): Promise<RuleConfig> {
  // TODO: Backend endpoint /api/config/rules/:id
  const response = await api.put<RuleConfig>(`/api/config/rules/${id}`, rule);
  return response.data;
}

async deleteRule(id: string): Promise<void> {
  // TODO: Backend endpoint /api/config/rules/:id
  await api.delete(`/api/config/rules/${id}`);
}

async syncRuleFromRepo(id: string): Promise<{ success: boolean; message: string }> {
  // TODO: Backend endpoint /api/config/rules/:id/sync
  const response = await api.post(`/api/config/rules/${id}/sync`);
  return response.data;
}

// MCP Servers
async getMcpServers(): Promise<McpServer[]> {
  // TODO: Backend endpoint /api/mcp-servers
  const response = await api.get<McpServer[]>('/api/mcp-servers');
  return response.data;
}

async createMcpServer(server: McpServerCreate): Promise<McpServer> {
  // TODO: Backend endpoint /api/mcp-servers
  const response = await api.post<McpServer>('/api/mcp-servers', server);
  return response.data;
}

async updateMcpServer(id: string, server: Partial<McpServerCreate>): Promise<McpServer> {
  // TODO: Backend endpoint /api/mcp-servers/:id
  const response = await api.put<McpServer>(`/api/mcp-servers/${id}`, server);
  return response.data;
}

async deleteMcpServer(id: string): Promise<void> {
  // TODO: Backend endpoint /api/mcp-servers/:id
  await api.delete(`/api/mcp-servers/${id}`);
}

async testMcpServer(id: string): Promise<{ success: boolean; message: string; latency?: number }> {
  // TODO: Backend endpoint /api/mcp-servers/:id/test
  const response = await api.post(`/api/mcp-servers/${id}/test`);
  return response.data;
}

// Enhanced provider config (extends existing getApiConfig/updateApiConfig)
async testProviderConnection(config: ProviderConfig): Promise<{ success: boolean; message: string; model_info?: any }> {
  // TODO: Backend endpoint /api/config/api-keys/test
  const response = await api.post('/api/config/api-keys/test', config);
  return response.data;
}
```

**Utility Functions** (new file `frontend/src/lib/utils.ts`):

```typescript
import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

**Modified Functions**:

The existing API client methods (`getApiConfig`, `updateApiConfig`) will remain unchanged but may be used by the new ProvidersTab component with enhanced UI.

## [Classes]

No new classes required - React functional components with hooks will be used throughout.

**Component Structure**:

All new components follow React functional component patterns with TypeScript:

1. **Settings Tab Components** (ProvidersTab, AgentTab, RulesTab, McpServersTab, AdvancedTab):
   - Use `useState` for local form state
   - Use `useEffect` for data fetching
   - Leverage `useToast` from shadcn for user feedback
   - Follow controlled component pattern for forms

2. **Layout Components** (Sidebar, AppShell):
   - Use React Router's `useLocation` for active route detection
   - Implement responsive behavior with Tailwind breakpoints
   - Use `Outlet` for nested routing

3. **shadcn/ui Components**:
   - All shadcn components are functional components with forwardRef where needed
   - Components use Radix UI primitives under the hood
   - Styled with Tailwind and CSS variables

## [Dependencies]

New package installations required for shadcn/ui and supporting libraries.

**Add to `frontend/package.json` dependencies**:

```json
{
  "dependencies": {
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "lucide-react": "^0.344.0",
    "@radix-ui/react-dialog": "^1.0.5",
    "@radix-ui/react-label": "^2.0.2",
    "@radix-ui/react-select": "^2.0.0",
    "@radix-ui/react-separator": "^1.0.3",
    "@radix-ui/react-slot": "^1.0.2",
    "@radix-ui/react-switch": "^1.0.3",
    "@radix-ui/react-tabs": "^1.0.4",
    "@radix-ui/react-toast": "^1.1.5",
    "tailwind-merge": "^2.2.1",
    "tailwindcss-animate": "^1.0.7"
  }
}
```

**Installation Command** (PowerShell):

```powershell
cd frontend; npm install class-variance-authority clsx lucide-react @radix-ui/react-dialog @radix-ui/react-label @radix-ui/react-select @radix-ui/react-separator @radix-ui/react-slot @radix-ui/react-switch @radix-ui/react-tabs @radix-ui/react-toast tailwind-merge tailwindcss-animate
```

**shadcn/ui CLI Setup**:

The shadcn/ui components will be added manually rather than using the CLI, since this gives more control over the setup in an existing project. All component files will be created directly in `frontend/src/components/ui/`.

## [Testing]

Testing strategy focused on visual verification and component functionality.

**Manual Testing Plan**:

1. **Theme Integration**:
   - Verify custom colors appear correctly across all components
   - Check that jet-black accent colors are used for primary actions
   - Confirm warm brown accents on borders and subtle elements
   - Test background colors (white-smoke-50 for page, white for cards)

2. **Layout & Navigation**:
   - Test sidebar navigation on desktop (links, active states, icons)
   - Test responsive behavior: sidebar collapses on mobile/tablet
   - Verify all routes (Dashboard, Projects, Runs, Settings) are accessible
   - Check scrolling behavior with long content

3. **Providers Tab**:
   - Test provider dropdown selection
   - Verify model input and validation
   - Test API key input (password masking)
   - Check temperature/max tokens sliders/inputs
   - Test "Test Connection" button (expect TODO backend response)
   - Verify form save functionality with toast notifications

4. **Agent Tab**:
   - Test persona textarea input
   - Verify all switches toggle correctly
   - Check that default values load properly
   - Test form submission with toast feedback

5. **Rules & Workflows Tab**:
   - Test rule type selector dropdown
   - Verify dialog opens for editing rules
   - Test monospace styling for code-like content
   - Check "Sync from repo" button behavior (TODO backend)

6. **MCP Servers Tab**:
   - Verify server list renders (or shows empty state)
   - Test "Add MCP Server" dialog opens
   - Check form validation in add/edit dialogs
   - Verify status pills display correctly (connected/error/disabled)
   - Test action buttons (Test, Edit, Disable) on server rows

7. **Advanced Tab**:
   - Confirm placeholder content displays

8. **Cross-Tab Functionality**:
   - Test tab switching preserves no unsaved data warnings if implemented
   - Verify tab indicator shows active state
   - Check keyboard navigation through tabs

**Browser Compatibility**:

Test in Chrome, Firefox, and Edge. The application should work in all modern browsers that support ES6+ and CSS Grid.

**Accessibility**:

- Verify keyboard navigation works for all interactive elements
- Check that form labels are properly associated
- Test screen reader compatibility (basic level)

**No Automated Tests**:

This implementation focuses on UI/UX transformation. Automated unit tests for individual components can be added later using React Testing Library if desired.

## [Implementation Order]

Step-by-step implementation sequence to minimize conflicts and ensure smooth integration.

**Phase 1: Foundation Setup**

1. **Install Dependencies**
   - Run npm install command for all shadcn/ui related packages
   - Verify installation completes without errors

2. **Configure Tailwind Theme**
   - Update `tailwind.config.js` with custom color palette
   - Add shadcn-specific configuration (animations, border radius)
   - Add path alias configuration for '@/' imports

3. **Setup CSS Variables**
   - Update `frontend/src/index.css` with CSS custom properties
   - Define color variables for light mode (dark mode optional)
   - Add base styles for shadcn components

4. **Update TypeScript Config**
   - Add path alias in `tsconfig.json` for '@/' -> './src/'
   - Ensure module resolution is correct

5. **Create Utility Functions**
   - Create `frontend/src/lib/utils.ts` with `cn()` function
   - Add necessary type definitions

**Phase 2: Component Library**

6. **Create Core shadcn/ui Components**
   - Create `frontend/src/components/ui/` directory
   - Add Button component
   - Add Card components (Card, CardHeader, CardTitle, etc.)
   - Add Input, Label, Textarea components
   - Add Switch component
   - Add Select component
   - Test each component in isolation by temporarily adding to existing page

7. **Create Advanced shadcn/ui Components**
   - Add Tabs components
   - Add Dialog component
   - Add Separator component
   - Add Badge component
   - Add Toast components and useToast hook

**Phase 3: Layout Transformation**

8. **Create New Layout Components**
   - Create `frontend/src/components/Sidebar.tsx` with navigation items
   - Create `frontend/src/components/AppShell.tsx` with sidebar + main content layout
   - Add Lucide React icons for navigation

9. **Update App.tsx**
   - Replace Layout component with AppShell
   - Test that routing still works for all pages

10. **Verify Existing Pages**
    - Check Dashboard, Projects, Runs, AdminPanel still render correctly
    - Fix any styling issues caused by new layout

**Phase 4: Type System Extensions**

11. **Extend TypeScript Types**
    - Add AgentConfig, RuleConfig, McpServer types to `frontend/src/types/index.ts`
    - Add ProviderConfig extension
    - Add form state types

12. **Extend API Client**
    - Add new methods for agent config, rules, MCP servers
    - Add test connection method for providers
    - Mark all new methods with TODO comments for backend endpoints

**Phase 5: Settings Page Rebuild**

13. **Create ProvidersTab Component** ✅ WORKS NOW
    - Build enhanced version of current Settings page
    - Use shadcn Card, Input, Select, Button components
    - Connect to existing `/api/config/api-keys` endpoints (GET/POST)
    - Add temperature/max tokens as frontend-only optional fields (stored in localStorage for now)
    - Test connection button shows "Feature coming soon" message (backend TODO)
    - Add proper form validation and toast notifications
    - This tab is fully functional with current backend

14. **Create AgentTab Component** ⚠️ NEEDS BACKEND
    - Add persona textarea with monospace styling
    - Add autonomy switches (file writes, shell commands, approval)
    - Add default settings inputs
    - Use mock/default data for now (no backend endpoints yet)
    - Add clear "Backend Integration Required" banner
    - Add TODO comments marking where `/api/config/agent` endpoints will connect
    - Form saves to localStorage temporarily until backend ready

15. **Create RulesTab Component** ⚠️ NEEDS BACKEND
    - Build rule type selector
    - Create rule list/cards showing example rules (mock data)
    - Implement edit dialog with textarea
    - Add sync from repo button (disabled with "Coming soon" tooltip)
    - Style code content with monospace font
    - Add TODO comments marking where `/api/config/rules` endpoints will connect
    - Show "Backend Integration Required" banner

16. **Create McpServersTab Component** ⚠️ NEEDS BACKEND
    - Build server list/table with status pills
    - Show empty state with "Add MCP Server" call-to-action
    - Create add/edit server dialog with form wizard (UI only, saves to localStorage)
    - Add conditional auth fields based on auth method
    - Test/Edit/Disable buttons show "Backend integration required" message
    - Add TODO comments marking where `/api/mcp-servers` endpoints will connect
    - Show "Backend Integration Required" banner

17. **Create AdvancedTab Component**
    - Create simple placeholder card with "Coming soon" message

18. **Rebuild Settings.tsx**
    - Replace entire file with new tabbed implementation
    - Import all five tab components
    - Use shadcn Tabs component for tab navigation
    - Add proper page header and description
    - Test tab switching

**Phase 6: Polish & Refinement**

19. **Responsive Testing**
    - Test sidebar collapse on mobile
    - Adjust spacing and layout for tablet/mobile
    - Ensure forms are usable on smaller screens

20. **Visual Polish**
    - Fine-tune colors and spacing throughout
    - Ensure consistent use of accent colors
    - Add hover states and transitions where needed
    - Check focus states for accessibility

21. **Error States & Loading**
    - Add loading skeletons where appropriate
    - Implement error boundaries for robustness
    - Add empty states for lists/tables

22. **Documentation Comments**
    - Add JSDoc comments to complex components
    - Document props interfaces
    - Add TODO comments clearly marking backend integration points

**Phase 7: Final Verification**

23. **End-to-End Testing**
    - Walk through all settings tabs
    - Test all form submissions
    - Verify toast notifications work
    - Check console for errors or warnings

24. **Cross-Browser Testing**
    - Test in Chrome, Firefox, Edge
    - Fix any browser-specific issues

25. **Code Quality Review**
    - Remove console.log statements
    - Ensure consistent code formatting
    - Check for unused imports
    - Verify ESLint passes

**Phase 8: Deployment Preparation**

26. **Build Test**
    - Run `npm run build` to ensure production build succeeds
    - Check bundle size is reasonable
    - Test production build locally with `npm run preview`

27. **Documentation Update**
    - Update README if needed with new component structure
    - Document custom color palette usage
    - Note any breaking changes from old Settings page

---

## Summary

This implementation transforms a basic frontend into a professional GitHub-style dashboard with:
- **27 implementation steps** organized into 8 phases
- **14 new component files** (shadcn/ui library)
- **5 new settings tab components** (1 fully functional NOW, 4 with mock data)
- **2 new layout components**
- **15+ new API methods** (some working NOW, others with TODO markers)
- **10+ new TypeScript types** (aligned with existing backend schemas)
- **10+ new dependencies**

### Backend Compatibility Status:

**✅ Works NOW (Immediate Value)**:
- ProvidersTab with full API integration (`/api/config/api-keys`)
- Projects page (already functional)
- Runs page (already functional)
- New UI/UX improvements across all pages

**⚠️ Needs Backend (Future Enhancement)**:
- AgentTab (needs `/api/config/agent` endpoints)
- RulesTab (needs `/api/config/rules` endpoints)
- McpServersTab (needs `/api/mcp-servers` endpoints)
- Test connection feature (needs `/api/config/api-keys/test` endpoint)

The phased approach ensures each layer (foundation → components → layout → types → features → polish) is solid before moving forward. Features that need backend endpoints will display clear "Backend Integration Required" banners and store data temporarily in localStorage, making it straightforward to wire up real endpoints incrementally without breaking the UI.
