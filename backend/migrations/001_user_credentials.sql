-- Migration: Add user credentials and workspace path
-- Date: 2024-12-08
-- Description: Adds support for per-user GitHub credentials and persistent workspaces

-- 1. Create user_git_credentials table
CREATE TABLE IF NOT EXISTS user_git_credentials (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    slack_user_id VARCHAR(255) NOT NULL,
    slack_username VARCHAR(255),
    github_username VARCHAR(255),
    github_access_token TEXT,
    github_refresh_token TEXT,
    token_expires_at TIMESTAMP,
    git_user_name VARCHAR(255),
    git_user_email VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_user_git_credentials_tenant_slack_user UNIQUE (tenant_id, slack_user_id)
);

CREATE INDEX IF NOT EXISTS idx_user_git_credentials_tenant_id ON user_git_credentials(tenant_id);
CREATE INDEX IF NOT EXISTS idx_user_git_credentials_slack_user_id ON user_git_credentials(slack_user_id);

-- 2. Add workspace_path to projects
ALTER TABLE projects ADD COLUMN IF NOT EXISTS workspace_path VARCHAR(512);

-- Initialize workspace_path for existing projects
UPDATE projects 
SET workspace_path = '/home/app/workspaces/project-' || id::text
WHERE workspace_path IS NULL;

-- 3. Add user fields to runs
ALTER TABLE runs ADD COLUMN IF NOT EXISTS slack_user_id VARCHAR(255);
ALTER TABLE runs ADD COLUMN IF NOT EXISTS user_git_credential_id UUID;

-- Add foreign key constraint
ALTER TABLE runs 
ADD CONSTRAINT fk_runs_user_git_credential 
FOREIGN KEY (user_git_credential_id) 
REFERENCES user_git_credentials(id) 
ON DELETE SET NULL;

-- Verification queries
SELECT 'user_git_credentials table created' as status, COUNT(*) as count FROM user_git_credentials;
SELECT 'projects updated' as status, COUNT(*) as count FROM projects WHERE workspace_path IS NOT NULL;
SELECT 'runs table updated' as status, COUNT(*) as total_runs FROM runs;
