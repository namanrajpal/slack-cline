"""Add user credentials and workspace path

Revision ID: 001_user_credentials
Revises: 
Create Date: 2024-12-08

This migration adds:
1. user_git_credentials table for per-user GitHub auth
2. workspace_path column to projects for persistent workspaces
3. user_git_credential_id and slack_user_id columns to runs
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_user_credentials'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create user_git_credentials table
    op.create_table(
        'user_git_credentials',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', sa.String(255), nullable=False, index=True),
        sa.Column('slack_user_id', sa.String(255), nullable=False, index=True),
        sa.Column('slack_username', sa.String(255), nullable=True),
        sa.Column('github_username', sa.String(255), nullable=True),
        sa.Column('github_access_token', sa.Text(), nullable=True),
        sa.Column('github_refresh_token', sa.Text(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(), nullable=True),
        sa.Column('git_user_name', sa.String(255), nullable=True),
        sa.Column('git_user_email', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('tenant_id', 'slack_user_id', name='uq_user_git_credentials_tenant_slack_user')
    )
    
    # Add workspace_path to projects
    op.add_column('projects', sa.Column('workspace_path', sa.String(512), nullable=True))
    
    # Add user_git_credential_id to runs
    op.add_column('runs', sa.Column('user_git_credential_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_runs_user_git_credential',
        'runs', 'user_git_credentials',
        ['user_git_credential_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Add slack_user_id to runs
    op.add_column('runs', sa.Column('slack_user_id', sa.String(255), nullable=True))
    
    # Initialize workspace_path for existing projects
    # Format: /home/app/workspaces/project-{id}
    op.execute("""
        UPDATE projects 
        SET workspace_path = '/home/app/workspaces/project-' || id::text
        WHERE workspace_path IS NULL
    """)


def downgrade():
    # Remove columns from runs
    op.drop_constraint('fk_runs_user_git_credential', 'runs', type_='foreignkey')
    op.drop_column('runs', 'user_git_credential_id')
    op.drop_column('runs', 'slack_user_id')
    
    # Remove column from projects
    op.drop_column('projects', 'workspace_path')
    
    # Drop user_git_credentials table
    op.drop_table('user_git_credentials')
