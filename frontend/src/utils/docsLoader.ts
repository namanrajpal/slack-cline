// Import markdown files using Vite's raw import
import readmeContent from '../../../docs/README.md?raw';
import quickstartContent from '../../../docs/getting-started/quickstart.md?raw';
import dashboardContent from '../../../docs/user-guide/dashboard.md?raw';
import architectureOverviewContent from '../../../docs/architecture/overview.md?raw';
import multiProjectContent from '../../../docs/architecture/multi-project.md?raw';
import debuggingContent from '../../../docs/development/debugging.md?raw';
import slackFormattingContent from '../../../docs/development/slack-formatting.md?raw';

export const docsContent: Record<string, string> = {
  'index': readmeContent,
  'getting-started/quickstart': quickstartContent,
  'user-guide/dashboard': dashboardContent,
  'architecture/overview': architectureOverviewContent,
  'architecture/multi-project': multiProjectContent,
  'development/debugging': debuggingContent,
  'development/slack-formatting': slackFormattingContent,
};

export function getDocContent(slug: string): string | null {
  return docsContent[slug] || null;
}
