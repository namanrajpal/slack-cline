"""
Slack Message Formatter

Utilities for converting Markdown to Slack mrkdwn format.
Handles mechanical cleanup and safety transformations before posting to Slack.
"""

import re
from typing import Optional

from utils.logging import get_logger

logger = get_logger("slack.formatter")


def format_for_slack(text: str) -> str:
    """
    Convert Markdown-style formatting to Slack mrkdwn.
    
    This is a mechanical safety net that cleans up common Markdown patterns
    that don't work in Slack. The agent should ideally generate Slack-native
    formatting, but this catches any issues.
    
    Transformations:
    - Convert `## Heading` → `*Heading*` (bold line)
    - Normalize `**bold**` → `*bold*` (Slack uses single asterisks)
    - Escape special characters: & < >
    - Ensure code blocks are properly closed
    
    Args:
        text: Message text to format
    
    Returns:
        Slack mrkdwn formatted text
    """
    if not text:
        return text
    
    lines = text.split('\n')
    formatted_lines = []
    in_code_block = False
    
    for line in lines:
        # Track code block state
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
            formatted_lines.append(line)
            continue
        
        # Don't transform content inside code blocks
        if in_code_block:
            formatted_lines.append(line)
            continue
        
        # Convert Markdown headings to bold lines
        # #### Heading → *Heading*
        if line.startswith('#### '):
            line = '*' + line[5:].strip() + '*'
        # ### Heading → *Heading*
        elif line.startswith('### '):
            line = '*' + line[4:].strip() + '*'
        # ## Heading → *Heading*
        elif line.startswith('## '):
            line = '*' + line[3:].strip() + '*'
        # # Heading → *Heading*
        elif line.startswith('# '):
            line = '*' + line[2:].strip() + '*'
        
        # Normalize bold: **text** → *text*
        # But preserve already-correct *text* and avoid breaking ***text***
        line = re.sub(r'\*\*\*(.+?)\*\*\*', r'***\1***', line)  # Preserve ***bold italic***
        line = re.sub(r'\*\*(.+?)\*\*', r'*\1*', line)  # **bold** → *bold*
        
        # Escape special HTML characters (but not in links or code)
        # Slack requires & < > to be escaped, but only outside of special contexts
        # We'll do a simple escape that avoids breaking existing <URL|text> patterns
        if not re.search(r'<[^>]+>', line) and '`' not in line:
            line = line.replace('&', '&amp;')
            # Only escape < > if they're not part of Slack syntax
            if not re.search(r'<[@#!][^>]+>', line):
                line = line.replace('<', '&lt;').replace('>', '&gt;')
        
        formatted_lines.append(line)
    
    result = '\n'.join(formatted_lines)
    
    # Log if we made significant changes
    if result != text:
        changes = []
        if '##' in text:
            changes.append("converted headings")
        if '**' in text and '**' not in result:
            changes.append("normalized bold")
        if changes:
            logger.debug(f"Slack formatting applied: {', '.join(changes)}")
    
    return result


def escape_slack_special_chars(text: str) -> str:
    """
    Escape special Slack characters: & < >
    
    This is a stricter escape that should be used for plain text
    that definitely doesn't contain any Slack markup.
    
    Args:
        text: Text to escape
    
    Returns:
        Escaped text
    """
    return (
        text.replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
    )


def validate_code_blocks(text: str) -> str:
    """
    Ensure code blocks are properly closed.
    
    If we find an odd number of ``` markers, adds a closing marker.
    
    Args:
        text: Text to validate
    
    Returns:
        Text with balanced code blocks
    """
    code_block_count = text.count('```')
    
    if code_block_count % 2 != 0:
        logger.warning("Found unclosed code block, adding closing marker")
        return text + '\n```'
    
    return text


def format_message_safely(text: str) -> str:
    """
    Full pipeline: format for Slack with all safety checks.
    
    This is the main entry point that should be used before
    posting any message to Slack.
    
    Args:
        text: Message text to format
    
    Returns:
        Fully formatted and validated Slack mrkdwn text
    """
    text = format_for_slack(text)
    text = validate_code_blocks(text)
    return text
