## Brief overview

Project-specific documentation guidelines for slack-cline. Ensures all major features are properly documented and implementation plans are organized systematically.

## Documentation requirements

- Always add documentation for any major feature implementation
- Documentation should be placed in the appropriate location within the `docs/` structure
- Follow the existing documentation hierarchy: getting-started/, user-guide/, architecture/, development/
- Update the main `docs/README.md` index when adding new documentation files
- Keep documentation current with implementation - deprecate outdated docs properly

## Documentation structure

- **Getting Started** (`docs/getting-started/`) - Setup guides, quickstart, first-time user tutorials
- **User Guide** (`docs/user-guide/`) - Feature usage, Slack commands, dashboard workflows
- **Architecture** (`docs/architecture/`) - System design, technical deep dives, component diagrams
- **Development** (`docs/development/`) - Local setup, debugging, API reference, contribution guides
- **Archive** (`docs/archive/`) - Outdated documentation kept for historical reference

## Implementation plans

- Create implementation plans in a separate dedicated folder: `docs/implementation-plans/`
- Use descriptive, specific filenames for implementation plans (e.g., `multi-project-llm-classification.md`, `agent-conversation-model.md`)
- Include clear sections: Overview, Technical Approach, Implementation Steps, Testing Strategy
- Archive implementation plans to `docs/archive/` once feature is complete and documented in main docs

## Documentation content guidelines

- Use friendly, approachable tone matching Sline's personality
- Include code examples where applicable
- Add troubleshooting sections for complex features
- Use diagrams and screenshots for visual clarity
- Keep documentation DRY - link to existing docs rather than duplicating

## When to document

- **Always document**: New user-facing features, API changes, architecture modifications, new workflows
- **Update existing docs**: Bug fixes that change behavior, configuration changes, deprecated features
- **Implementation plans**: Before starting major features or architectural changes
