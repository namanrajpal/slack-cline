"""
Slack Web API client wrapper.

This module provides a simplified interface for posting messages and updates
to Slack channels using the Slack Web API.
"""

import json
from typing import Dict, List, Optional, Any

import httpx
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from config import settings
from utils.logging import get_logger, log_slack_event

logger = get_logger("slack.client")


class SlackClient:
    """
    Wrapper for Slack Web API operations.
    
    This client handles posting messages, updating threads, and managing
    interactive components in Slack channels.
    """
    
    def __init__(self, bot_token: str = None):
        """
        Initialize Slack client.
        
        Args:
            bot_token: Slack bot token (defaults to config)
        """
        self.bot_token = bot_token or settings.slack_bot_token
        if self.bot_token:
            self.client = WebClient(token=self.bot_token)
        else:
            self.client = None
            logger.warning("Slack bot token not configured, client disabled")
    
    def is_enabled(self) -> bool:
        """Check if Slack client is properly configured."""
        return self.client is not None
    
    async def post_message(
        self,
        channel: str,
        text: str,
        blocks: Optional[List[Dict]] = None,
        thread_ts: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Post a message to a Slack channel.
        
        Args:
            channel: Channel ID to post to
            text: Message text (fallback for blocks)
            blocks: Block Kit blocks for rich formatting
            thread_ts: Thread timestamp to reply in thread
            
        Returns:
            dict: Slack API response
            
        Raises:
            RuntimeError: If Slack API call fails
        """
        if not self.is_enabled():
            logger.warning("Slack client not configured, skipping message post")
            return {"ok": False, "error": "client_not_configured"}
        
        try:
            response = self.client.chat_postMessage(
                channel=channel,
                text=text,
                blocks=blocks,
                thread_ts=thread_ts
            )
            
            log_slack_event(
                "message_posted",
                channel_id=channel,
                thread_ts=thread_ts,
                success=response.get("ok", False)
            )
            
            return response.data
            
        except SlackApiError as e:
            logger.error(f"Slack API error posting message: {e.response['error']}")
            log_slack_event(
                "message_post_failed", 
                channel_id=channel,
                error=e.response["error"]
            )
            raise RuntimeError(f"Failed to post Slack message: {e.response['error']}")
        except Exception as e:
            logger.error(f"Unexpected error posting message: {e}")
            raise RuntimeError(f"Failed to post Slack message: {e}")
    
    async def update_message(
        self,
        channel: str,
        ts: str,
        text: str,
        blocks: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Update an existing Slack message.
        
        Args:
            channel: Channel ID where message exists
            ts: Timestamp of message to update
            text: New message text
            blocks: New Block Kit blocks
            
        Returns:
            dict: Slack API response
        """
        if not self.is_enabled():
            logger.warning("Slack client not configured, skipping message update")
            return {"ok": False, "error": "client_not_configured"}
        
        try:
            response = self.client.chat_update(
                channel=channel,
                ts=ts,
                text=text,
                blocks=blocks
            )
            
            log_slack_event(
                "message_updated",
                channel_id=channel,
                message_ts=ts,
                success=response.get("ok", False)
            )
            
            return response.data
            
        except SlackApiError as e:
            logger.error(f"Slack API error updating message: {e.response['error']}")
            raise RuntimeError(f"Failed to update Slack message: {e.response['error']}")
    
    async def post_delayed_response(
        self,
        response_url: str,
        text: str,
        blocks: Optional[List[Dict]] = None,
        response_type: str = "in_channel",
        replace_original: bool = False
    ) -> None:
        """
        Send a delayed response to a Slack interaction.
        
        This is used to update the original message or send follow-up
        messages using the response_url from slash commands.
        
        Args:
            response_url: Response URL from Slack interaction
            text: Message text
            blocks: Block Kit blocks
            response_type: "in_channel" or "ephemeral"
            replace_original: Whether to replace the original message
        """
        if not response_url:
            logger.warning("No response URL provided for delayed response")
            return
        
        payload = {
            "text": text,
            "response_type": response_type,
            "replace_original": replace_original
        }
        
        if blocks:
            payload["blocks"] = blocks
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    response_url,
                    json=payload,
                    timeout=30
                )
                response.raise_for_status()
            
            log_slack_event(
                "delayed_response_sent",
                response_type=response_type,
                success=True
            )
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error sending delayed response: {e}")
            log_slack_event("delayed_response_failed", error=str(e))
        except Exception as e:
            logger.error(f"Unexpected error sending delayed response: {e}")
            log_slack_event("delayed_response_failed", error=str(e))
    
    def create_run_status_blocks(
        self,
        task_prompt: str,
        status: str,
        message: str,
        run_id: str = None,
        show_cancel_button: bool = True
    ) -> List[Dict]:
        """
        Create Block Kit blocks for run status messages.
        
        Args:
            task_prompt: Original task description
            status: Current run status
            message: Status message
            run_id: Run ID for button actions
            show_cancel_button: Whether to show cancel button
            
        Returns:
            list: Block Kit blocks
        """
        # Status emoji mapping
        status_emojis = {
            "queued": "⏳",
            "running": "🔧", 
            "succeeded": "✅",
            "failed": "❌",
            "cancelled": "⏹️"
        }
        
        emoji = status_emojis.get(status, "🔍")
        
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{emoji} *Cline Run:* `{task_prompt}`"
                }
            },
            {
                "type": "section", 
                "text": {
                    "type": "mrkdwn",
                    "text": message
                }
            }
        ]
        
        # Add cancel button for active runs
        if show_cancel_button and status in ("queued", "running") and run_id:
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Cancel"
                        },
                        "style": "danger",
                        "action_id": "cancel_run",
                        "value": run_id
                    }
                ]
            })
        
        return blocks
    
    def create_progress_blocks(
        self,
        task_prompt: str,
        steps_completed: int,
        total_steps: int,
        current_step: str,
        run_id: str = None
    ) -> List[Dict]:
        """
        Create Block Kit blocks for run progress updates.
        
        Args:
            task_prompt: Original task description
            steps_completed: Number of completed steps
            total_steps: Total number of steps
            current_step: Description of current step
            run_id: Run ID for button actions
            
        Returns:
            list: Block Kit blocks
        """
        progress_text = f"Step {steps_completed + 1}/{total_steps}: {current_step}"
        progress_bar = "■" * steps_completed + "□" * (total_steps - steps_completed)
        
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🔧 *Cline Run:* `{task_prompt}`"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{progress_text}\n`{progress_bar}`"
                }
            }
        ]
        
        # Add cancel button
        if run_id:
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Cancel"
                        },
                        "style": "danger", 
                        "action_id": "cancel_run",
                        "value": run_id
                    }
                ]
            })
        
        return blocks


# Global client instance
_slack_client: Optional[SlackClient] = None


def get_slack_client() -> SlackClient:
    """
    Get or create the global Slack client instance.
    
    Returns:
        SlackClient: Client instance
    """
    global _slack_client
    if _slack_client is None:
        _slack_client = SlackClient()
    return _slack_client
