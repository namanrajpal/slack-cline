"""
GitHub OAuth flow for connecting user Git credentials.

This module handles the OAuth flow for users to connect their GitHub accounts,
storing credentials that will be used for git commit attribution.
"""

import secrets
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_session
from models.user_git_credential import UserGitCredentialModel
from utils.logging import get_logger

logger = get_logger("auth.github")

auth_router = APIRouter()

# Store OAuth state tokens temporarily (in production, use Redis)
_oauth_states = {}


@auth_router.get("/github/login")
async def github_login(
    tenant_id: Optional[str] = None,
    slack_user_id: Optional[str] = None,
    slack_username: Optional[str] = None,
    source: Optional[str] = None
):
    """
    Initiate GitHub OAuth flow.
    
    This endpoint is called when a user clicks "Connect GitHub" from Slack or admin panel.
    It redirects the user to GitHub's OAuth page.
    
    Query params:
        tenant_id: Tenant identifier (required for Slack, optional for admin)
        slack_user_id: Slack user ID (required for Slack, optional for admin)
        slack_username: Optional Slack username
        source: 'admin' if called from admin panel, None if from Slack
    """
    # Generate random state token to prevent CSRF
    state = secrets.token_urlsafe(32)
    
    # Store state with user info (expires after 10 minutes)
    _oauth_states[state] = {
        "tenant_id": tenant_id,
        "slack_user_id": slack_user_id,
        "slack_username": slack_username,
        "source": source
    }
    
    # Build GitHub OAuth URL
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": settings.github_oauth_redirect_uri,
        "scope": "user:email",  # We only need email, not repo access
        "state": state
    }
    
    github_url = f"https://github.com/login/oauth/authorize?{urlencode(params)}"
    
    logger.info(f"Redirecting user {slack_user_id} to GitHub OAuth")
    
    return RedirectResponse(url=github_url)


@auth_router.get("/github/callback")
async def github_callback(
    code: str,
    state: str,
    session: AsyncSession = Depends(get_session)
):
    """
    Handle GitHub OAuth callback.
    
    GitHub redirects here after user authorizes the app.
    We exchange the code for an access token and fetch user info.
    """
    # Verify state token
    if state not in _oauth_states:
        logger.error(f"Invalid OAuth state: {state}")
        raise HTTPException(status_code=400, detail="Invalid state token")
    
    user_info = _oauth_states.pop(state)
    tenant_id = user_info.get("tenant_id")
    slack_user_id = user_info.get("slack_user_id")
    slack_username = user_info.get("slack_username")
    source = user_info.get("source")
    is_admin_login = source == "admin"
    
    try:
        # Exchange code for access token
        async with httpx.AsyncClient() as client:
            # Step 1: Get access token
            token_response = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code,
                    "redirect_uri": settings.github_oauth_redirect_uri
                }
            )
            
            token_data = token_response.json()
            
            if "error" in token_data:
                logger.error(f"GitHub OAuth error: {token_data}")
                raise HTTPException(status_code=400, detail=token_data.get("error_description", "OAuth failed"))
            
            access_token = token_data.get("access_token")
            if not access_token:
                raise HTTPException(status_code=400, detail="No access token received")
            
            # Step 2: Get user info from GitHub
            user_response = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            
            github_user = user_response.json()
            
            # Step 3: Get user's email (might be separate call if not public)
            if not github_user.get("email"):
                email_response = await client.get(
                    "https://api.github.com/user/emails",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github.v3+json"
                    }
                )
                
                emails = email_response.json()
                # Find primary email
                primary_email = next(
                    (e for e in emails if e.get("primary")),
                    emails[0] if emails else None
                )
                
                if primary_email:
                    github_user["email"] = primary_email["email"]
        
        # Step 4: Store or update credentials in database (only for Slack users, not admin panel)
        if not is_admin_login and tenant_id and slack_user_id:
            credential = await UserGitCredentialModel.find_by_slack_user(
                session,
                tenant_id,
                slack_user_id
            )
            
            if credential:
                # Update existing
                credential.github_username = github_user.get("login")
                credential.github_access_token = access_token
                credential.git_user_name = github_user.get("name") or github_user.get("login")
                credential.git_user_email = github_user.get("email")
                credential.slack_username = slack_username
            else:
                # Create new
                credential = UserGitCredentialModel(
                    tenant_id=tenant_id,
                    slack_user_id=slack_user_id,
                    slack_username=slack_username,
                    github_username=github_user.get("login"),
                    github_access_token=access_token,
                    git_user_name=github_user.get("name") or github_user.get("login"),
                    git_user_email=github_user.get("email")
                )
                session.add(credential)
            
            await session.commit()
            
            logger.info(f"Successfully connected GitHub for user {slack_user_id}: {github_user.get('login')}")
        else:
            logger.info(f"Admin panel GitHub connection: {github_user.get('login')}")
        
        # Return success page
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>GitHub Connected</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }}
                .container {{
                    text-align: center;
                    background: rgba(255, 255, 255, 0.1);
                    padding: 3rem;
                    border-radius: 1rem;
                    backdrop-filter: blur(10px);
                }}
                .success-icon {{
                    font-size: 4rem;
                    margin-bottom: 1rem;
                }}
                h1 {{
                    margin: 0 0 1rem 0;
                }}
                .username {{
                    font-size: 1.2rem;
                    opacity: 0.9;
                    margin-bottom: 2rem;
                }}
                .info {{
                    font-size: 0.9rem;
                    opacity: 0.8;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success-icon">✅</div>
                <h1>GitHub Connected!</h1>
                <div class="username">@{github_user.get('login')}</div>
                <p class="info">All commits will now be attributed to:</p>
                <p class="info"><strong>{github_user.get('name') or github_user.get('login')}</strong></p>
                <p class="info">&lt;{github_user.get('email')}&gt;</p>
                <p style="margin-top: 2rem; opacity: 0.7;">You can close this window and return to Slack.</p>
            </div>
            <script>
                // Send token to opener window if exists (for admin panel)
                if (window.opener) {{
                    window.opener.postMessage({{
                        type: 'github_auth_success',
                        token: '{access_token}',
                        username: '{github_user.get('login')}',
                        name: '{github_user.get('name') or github_user.get('login')}',
                        email: '{github_user.get('email')}'
                    }}, '*');
                }}
                
                // Auto-close after 5 seconds
                setTimeout(() => {{
                    window.close();
                }}, 5000);
            </script>
        </body>
        </html>
        """)
        
    except Exception as e:
        logger.error(f"Error in GitHub OAuth callback: {e}", exc_info=True)
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Connection Failed</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                    color: white;
                }}
                .container {{
                    text-align: center;
                    background: rgba(255, 255, 255, 0.1);
                    padding: 3rem;
                    border-radius: 1rem;
                    backdrop-filter: blur(10px);
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div style="font-size: 4rem; margin-bottom: 1rem;">❌</div>
                <h1>Connection Failed</h1>
                <p>Failed to connect GitHub account.</p>
                <p style="opacity: 0.8; margin-top: 2rem;">Please try again from Slack.</p>
            </div>
        </body>
        </html>
        """, status_code=500)


@auth_router.post("/github/disconnect")
async def github_disconnect(
    tenant_id: str,
    slack_user_id: str,
    session: AsyncSession = Depends(get_session)
):
    """
    Disconnect user's GitHub account.
    
    Removes the stored GitHub credentials so commits will use default identity.
    """
    credential = await UserGitCredentialModel.find_by_slack_user(
        session,
        tenant_id,
        slack_user_id
    )
    
    if not credential:
        raise HTTPException(status_code=404, detail="No GitHub connection found")
    
    # Clear GitHub data
    credential.github_username = None
    credential.github_access_token = None
    credential.git_user_name = None
    credential.git_user_email = None
    
    await session.commit()
    
    logger.info(f"Disconnected GitHub for user {slack_user_id}")
    
    return {"status": "disconnected"}
