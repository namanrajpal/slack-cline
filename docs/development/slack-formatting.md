# Slack Message Formatting

**Status:** ✅ Implemented  
**Date:** December 10, 2025

## Problem

Sline's LLM agent (Claude) was generating responses using GitHub-style Markdown syntax (e.g., `## Headings`, `**bold**`), but Slack uses its own markup language called **mrkdwn**, which is a subset of Markdown with different rules. This caused raw formatting characters like `##` to appear in messages.

### Example Issue

**Agent Output:**
```markdown
## 🤖 Sline - AI Coding Teammate

This is **Sline**, a conversational AI assistant...

## What Makes It Special
- **Conversational**: Just @mention Sline
- **Smart**: Uses autonomous tools
```

**What Slack Showed:**
```
## 🤖 Sline - AI Coding Teammate

This is **Sline**, a conversational AI assistant...

## What Makes It Special
- **Conversational**: Just @mention Sline
- **Smart**: Uses autonomous tools
```

The `##` headings and `**bold**` showed as raw text instead of formatting.

## Solution

We implemented a **two-layer fix** following the architectural principle that the agent decides content while the gateway handles presentation:

### Layer 1: Agent Prompt (Primary Fix)

**File:** `backend/modules/agent/prompts.py`

Added comprehensive Slack mrkdwn formatting guidelines directly to the system prompt. This teaches the LLM to generate Slack-native formatting from the start.

**Key Guidelines Added:**
- ✅ Use `*bold*` (single asterisks), not `**bold**`
- ✅ Use `_italic_` (underscores)
- ✅ Use bold lines for section headers: `*Header*`
- ❌ No `#` or `##` headings
- ❌ No tables
- ❌ No HTML tags

**Example Formatting Rules:**
```
*Section Title*

Paragraph text here...

*What I Found*
- The auth module is in `src/auth.py`
- Uses JWT tokens

*Code snippet:*
```python
def verify_token(token):
    return jwt.decode(token)
```
```

### Layer 2: Presentation Safety Net

**File:** `backend/utils/slack_formatter.py`

Created a mechanical formatter that converts any remaining Markdown to mrkdwn as a safety net.

**Transformations:**
1. `## Heading` → `*Heading*` (bold line)
2. `### Heading` → `*Heading*`
3. `**bold**` → `*bold*`
4. Escapes special characters: `&` `<` `>`
5. Validates code blocks are properly closed

**Integration:**

Modified `backend/utils/slack_client.py` to apply formatting before every message:

```python
from utils.slack_formatter import format_message_safely

async def post_message(self, channel, text, ...):
    # Format text for Slack mrkdwn
    formatted_text = format_message_safely(text)
    
    response = self.client.chat_postMessage(
        channel=channel,
        text=formatted_text,
        ...
    )
```

## Slack mrkdwn Quick Reference

### What Works in Slack

| Feature | Syntax | Example |
|---------|--------|---------|
| Bold | `*text*` | *bold text* |
| Italic | `_text_` | _italic text_ |
| Strikethrough | `~text~` | ~struck text~ |
| Inline code | `` `code` `` | `inline code` |
| Code block | ` ```code``` ` | (multiline code) |
| Bullet | `- item` or `• item` | • Bullet point |
| Block quote | `> quote` | > Quoted text |
| Emoji | `:emoji_name:` | :wave: :rocket: |

### What Doesn't Work

- ❌ Headings: `#`, `##`, `###` (show as raw text)
- ❌ Double asterisks: `**bold**` (Slack uses single)
- ❌ Tables: `| col | col |` (not supported)
- ❌ HTML tags: `<b>bold</b>` (not rendered)
- ❌ Footnotes, task lists, definition lists

### Section Headers in Slack

Instead of Markdown headings, use **bold lines** followed by blank lines:

```
*Main Section*

Content goes here with normal text formatting.

*Another Section*

- Bullet point
- Another point
```

## Architecture Pattern

This solution follows the clean separation of concerns in Sline's architecture:

```
┌─────────────────────────┐
│   Agent Layer (LLM)     │  ← Taught "how to write for Slack"
│   - prompts.py          │     via system prompt
└───────────┬─────────────┘
            │
            │ (generates content)
            │
            ▼
┌─────────────────────────┐
│  Presentation Layer     │  ← Mechanical cleanup & safety
│  - slack_formatter.py   │     (convert remaining Markdown)
│  - slack_client.py      │     (apply before posting)
└─────────────────────────┘
            │
            │ (posts to Slack)
            │
            ▼
      Slack Web API
```

## Testing

### Manual Testing

1. **Start the backend:**
   ```powershell
   docker-compose up backend
   ```

2. **Send a test message via Admin Panel:**
   - Navigate to Dashboard → Admin Panel
   - Send a message with various formatting
   - Check the response in the conversation view

3. **Test in Slack:**
   - @mention Sline in a Slack channel
   - Ask questions that would trigger formatted responses
   - Verify no `##` or `**` appears in messages

### Expected Behavior

**Before Fix:**
```
## 🤖 What I Found
**Auth System:**
- Located in `src/auth.py`
```

**After Fix:**
```
*🤖 What I Found*
*Auth System:*
- Located in `src/auth.py`
```

## Files Modified

1. ✅ `backend/utils/slack_formatter.py` - **NEW** formatter utility
2. ✅ `backend/modules/agent/prompts.py` - Added Slack formatting context
3. ✅ `backend/utils/slack_client.py` - Integrated formatter

## Benefits

1. **Agent-First:** 90% of formatting is correct at generation time
2. **Safety Net:** Remaining issues are mechanically fixed
3. **Maintainable:** Clear separation between AI decisions and presentation
4. **Robust:** Works even if LLM occasionally slips into Markdown mode
5. **Extensible:** Easy to add more transformation rules

## Future Enhancements

- [ ] Add tests for `slack_formatter.py` with various edge cases
- [ ] Support for Slack Block Kit rich formatting (buttons, etc.)
- [ ] Handle nested formatting edge cases (e.g., bold inside code blocks)
- [ ] Add formatter for delayed responses and interactive messages

## References

- [Slack Formatting Reference](https://api.slack.com/reference/surfaces/formatting)
- [Slack mrkdwn Guide](https://www.markdownguide.org/tools/slack/)
- Original Issue: Raw `##` appearing in Slack messages

---

**Summary:** Sline now generates clean, Slack-native messages by teaching the LLM proper mrkdwn syntax and providing a mechanical safety net formatter.
