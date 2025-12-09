# Database Migrations

## Overview

This directory contains database migrations for adding user Git credentials and persistent workspace support.

## Migration 001: User Credentials and Workspace Path

**Date:** 2024-12-08

**Changes:**
1. Creates `user_git_credentials` table for per-user GitHub authentication
2. Adds `workspace_path` column to `projects` table
3. Adds `slack_user_id` and `user_git_credential_id` columns to `runs` table

## How to Apply Migration

### Option 1: Using Docker Compose (Recommended)

```bash
# Connect to the database container
docker-compose exec postgres psql -U sline -d sline

# Run the migration
\i /path/to/migrations/001_user_credentials.sql
```

### Option 2: Direct SQL Execution

```bash
# From host machine
psql -h localhost -U sline -d sline -f backend/migrations/001_user_credentials.sql
```

### Option 3: Using Python Alembic (if configured)

```bash
# From backend directory
cd backend
alembic upgrade head
```

## Verification

After running the migration, verify the changes:

```sql
-- Check new table exists
SELECT table_name FROM information_schema.tables 
WHERE table_name = 'user_git_credentials';

-- Check new columns exist
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'projects' AND column_name = 'workspace_path';

SELECT column_name FROM information_schema.columns 
WHERE table_name = 'runs' AND column_name IN ('slack_user_id', 'user_git_credential_id');

-- Check foreign key exists
SELECT constraint_name FROM information_schema.table_constraints 
WHERE table_name = 'runs' AND constraint_name = 'fk_runs_user_git_credential';
```

## Rollback

If you need to rollback the migration:

```sql
-- Remove foreign key
ALTER TABLE runs DROP CONSTRAINT IF EXISTS fk_runs_user_git_credential;

-- Remove columns from runs
ALTER TABLE runs DROP COLUMN IF EXISTS user_git_credential_id;
ALTER TABLE runs DROP COLUMN IF EXISTS slack_user_id;

-- Remove column from projects
ALTER TABLE projects DROP COLUMN IF EXISTS workspace_path;

-- Drop table
DROP TABLE IF EXISTS user_git_credentials;
```

## Next Steps After Migration

1. **Restart backend service** to load new models
2. **Update code** to use new fields (orchestrator, CLI client)
3. **Implement GitHub OAuth** flow for users to connect
4. **Test workspace reuse** logic

## Notes

- All existing projects will have `workspace_path` automatically set
- User credentials are nullable to support gradual rollout
- Foreign keys use `ON DELETE SET NULL` for safety
