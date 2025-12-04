"""
Slack webhook signature verification.

This module handles verification of incoming Slack webhook requests to ensure
they are authentic and haven't been tampered with.
"""

import hashlib
import hmac
import time
from typing import Optional

from fastapi import HTTPException, status

from config import settings
from utils.logging import get_logger

logger = get_logger("slack.verification")


def verify_slack_signature(
    timestamp: str,
    body: bytes,
    signature: str,
    signing_secret: Optional[str] = None
) -> bool:
    """
    Verify a Slack webhook signature to ensure the request is authentic.
    
    Slack signs each request with a signature that we can verify using the
    signing secret configured in our Slack app.
    
    Args:
        timestamp: X-Slack-Request-Timestamp header value
        body: Raw request body bytes
        signature: X-Slack-Signature header value
        signing_secret: Slack signing secret (defaults to config value)
        
    Returns:
        bool: True if signature is valid, False otherwise
        
    Raises:
        HTTPException: If request is too old or signature format is invalid
    """
    if not signing_secret:
        signing_secret = settings.slack_signing_secret
    
    if not signing_secret:
        logger.warning("Slack signing secret not configured, skipping verification")
        return True  # Allow requests if no secret is configured (dev mode)
    
    # Check timestamp to prevent replay attacks
    current_time = int(time.time())
    request_time = int(timestamp)
    
    if abs(current_time - request_time) > 60 * 5:  # 5 minutes
        logger.warning("Request timestamp too old", timestamp=timestamp, current_time=current_time)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Request timestamp is too old"
        )
    
    # Verify signature format
    if not signature.startswith("v0="):
        logger.warning("Invalid signature format", signature=signature)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature format"
        )
    
    # Calculate expected signature
    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    expected_signature = "v0=" + hmac.new(
        signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures using secure comparison
    is_valid = hmac.compare_digest(expected_signature, signature)
    
    if not is_valid:
        logger.warning(
            "Invalid Slack signature",
            expected_signature=expected_signature,
            received_signature=signature
        )
    
    return is_valid


def require_slack_verification(timestamp: str, body: bytes, signature: str) -> None:
    """
    Require Slack signature verification, raising an exception if invalid.
    
    This is a helper function for endpoints that need to enforce verification.
    
    Args:
        timestamp: X-Slack-Request-Timestamp header value
        body: Raw request body bytes  
        signature: X-Slack-Signature header value
        
    Raises:
        HTTPException: If signature verification fails
    """
    if not verify_slack_signature(timestamp, body, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Slack signature"
        )


def extract_slack_headers(request) -> tuple[str, str]:
    """
    Extract Slack-specific headers from a FastAPI request.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        tuple: (timestamp, signature) from headers
        
    Raises:
        HTTPException: If required headers are missing
    """
    timestamp = request.headers.get("X-Slack-Request-Timestamp")
    signature = request.headers.get("X-Slack-Signature")
    
    if not timestamp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Slack-Request-Timestamp header"
        )
    
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Slack-Signature header"
        )
    
    return timestamp, signature
