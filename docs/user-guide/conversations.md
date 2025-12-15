# Conversations Guide

Understanding Sline's conversation-based model and how it differs from traditional task-based approaches.

---

## 🧵 What is the Conversation Model?

Sline uses a **conversation-based architecture** instead of a traditional "run" or "task" model. This means:

- Each Slack thread is a **persistent conversation**
- Agent remembers full conversation history
- Multi-turn interactions feel natural
- State survives server restarts

---

## Current Conversation Model ✅

✅ **Thread-based**: Conversations span multiple messages  
✅ **Persistent**: Full history saved to database  
✅ **Slack-native**: Designed for natural chat  
✅ **Stateful**: Agent remembers previous messages  

```
User: "List files in src/"
→ Conversation created
→ Agent responds with file list
→ State saved with full history

User: "Read main.py"
→ Same conversation continues
→ Agent remembers previous message! ✅
→ Can reference earlier context
```

---

## 🔑 Key Concepts

### One Thread = One Conversation

Each Slack thread creates a unique conversation identified by:
- `channel_id`: Which Slack channel
- `thread_ts`: Thread timestamp (unique ID)

```python
# Conversation identifier
conversation_key = (channel_id, thread_ts)

# Example
conversation = ("C0A0B5H7RC3", "1765353374.822169")
```

### Conversation State

Everything is persisted in PostgreSQL:

```python
{
    "messages": [
        HumanMessage("What files are here?"),
        AIMessage("I found: README.md, src/, tests/"),
        HumanMessage("Read the README"),
        AIMessage("The README contains...")
    ],
    "workspace_path": "/data/workspaces/<project-uuid>",
    "project_id": "<uuid>",
    "channel_id": "C0A0B5H7RC3",
    "thread_ts": "1765353374.822169",
    "user_id": "U0A023XQNVD",
    "mode": "chat",  # chat | planning | awaiting_approval | executing
    "files_context": {}  # Recently accessed files cache
}
```

### Multi-Turn Memory

The agent sees **entire conversation history**:

```
Turn 1:
User: "What's in this project?"
Agent: [Uses list_files tool] "This project has..."

Turn 2:
User: "Can you read the main file?"
Agent: [Remembers Turn 1, knows which files exist]
       "Sure! Reading main.py from the src directory..."

Turn 3:
User: "What does that function do?"
Agent: [Remembers Turn 1 & 2, knows context]
       "The function we just looked at does..."
```

---

## 🔄 Conversation Lifecycle

### 1. New Conversation (Top-Level @mention)

```
User posts in channel: "@sline explain how auth works"

Backend:
├─ Receives Slack event
├─ Extracts: channel_id, message_ts, text
├─ Creates conversation_key: (channel_id, message_ts)
├─ Checks database → Not found (new conversation)
├─ Classifies project based on message
├─ Creates workspace directory
└─ Initializes SlineState with empty messages

Agent:
├─ Appends HumanMessage to state
├─ Invokes LangGraph workflow
├─ Uses tools autonomously (read_file, search, etc.)
├─ Generates response
└─ Appends AIMessage to state

Database:
├─ Serializes state to JSON
├─ Inserts ConversationModel record
└─ Saves to conversations table

Slack:
├─ Posts response in thread
└─ Thread becomes conversation container
```

### 2. Continuing Conversation (Thread Reply)

```
User replies in thread: "@sline can you show me the code?"

Backend:
├─ Receives Slack event
├─ Extracts: channel_id, thread_ts (original message)
├─ Creates conversation_key: (channel_id, thread_ts)
└─ Checks database → Found! (existing conversation)

Agent:
├─ Loads state_json from database
├─ Deserializes → Full message history!
├─ Appends new HumanMessage
├─ Invokes LangGraph (sees ALL previous messages)
├─ Uses context from earlier in conversation
├─ Generates contextual response
└─ Appends AIMessage

Database:
├─ Updates state_json
├─ Increments message_count
└─ Updates updated_at timestamp

Slack:
└─ Posts response in same thread
```

---

## 💾 Database Structure

### Conversations Table

```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY,
    channel_id VARCHAR(255) NOT NULL,
    thread_ts VARCHAR(255) NOT NULL,
    project_id UUID REFERENCES projects(id),
    state_json JSON NOT NULL,  -- Serialized SlineState
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_user_id VARCHAR(255),
    message_count INTEGER DEFAULT 0,
    UNIQUE(channel_id, thread_ts)
);
```

### State JSON Format

```json
{
  "messages": [
    {
      "type": "human",
      "content": "What files are here?",
      "additional_kwargs": {},
      "example": false
    },
    {
      "type": "ai",
      "content": "This project contains...",
      "additional_kwargs": {},
      "tool_calls": [
        {
          "name": "list_files",
          "args": {"path": ".", "recursive": false},
          "id": "call_123"
        }
      ]
    }
  ],
  "workspace_path": "/data/workspaces/abc-123",
  "project_id": "abc-123",
  "channel_id": "C123",
  "thread_ts": "1234567890.123",
  "mode": "chat"
}
```

---

## 🧪 Testing Conversations

### Using Admin Panel

The Admin Panel lets you test conversation flow without Slack:

**Step 1: Start Conversation**
```
Project: my-project
Message: "What files are in this project?"
→ Click "Send"
→ Agent responds with file listing
```

**Step 2: Continue Conversation**
```
Message: "Can you read the README?"
→ Click "Send"
→ Agent remembers previous message ✅
→ Knows which files exist from Step 1
```

**Step 3: Reference Earlier Context**
```
Message: "What did you say about the src directory?"
→ Click "Send"
→ Agent recalls information from Step 1 ✅
→ Provides contextual answer
```

### Verifying in Database

```powershell
docker-compose exec db psql -U postgres -d slack_cline

# View active conversations
SELECT 
    channel_id,
    thread_ts,
    message_count,
    created_at,
    updated_at
FROM conversations
ORDER BY updated_at DESC;

# View conversation state
SELECT state_json::json->'messages' 
FROM conversations 
WHERE channel_id = 'test_channel';

# Count messages per conversation
SELECT 
    channel_id,
    thread_ts,
    message_count,
    json_array_length(state_json::json->'messages') as actual_messages
FROM conversations;

\q
```

---

## 🎯 Conversation Modes

Conversations can be in different modes based on what the user needs:

### Chat Mode (Current)

Default mode for Q&A and exploration.

**Capabilities:**
- Answer questions
- Read files
- Search code
- List directories
- Explain concepts

**Example:**
```
User: "Where is the authentication logic?"
Agent: [Uses search_files, reads relevant files]
       "The auth logic is in src/auth/..."
```

### Planning Mode (Phase 2)

Creating implementation plans before executing.

**Capabilities:**
- Analyze requirements
- Create step-by-step plans
- Estimate complexity
- Identify dependencies

**Example:**
```
User: "Create a plan to add JWT authentication"
Agent: [Switches to planning mode]
       "Here's the implementation plan:
        1. Install PyJWT library
        2. Create auth middleware
        3. Update user model..."
```

### Awaiting Approval Mode (Phase 2)

Waiting for user confirmation before executing plan.

**Example:**
```
Agent: "Plan created. Approve to execute?"
User: "👍" (Slack reaction)
Agent: [Switches to executing mode]
```

### Executing Mode (Phase 2)

Actively making changes with write tools.

**Capabilities:**
- Create/modify files
- Run commands
- Commit changes
- Create PRs

---

## 🔍 Conversation Context

### What Agent Remembers

✅ **All previous messages** in the thread  
✅ **Tool calls** and their results  
✅ **Files accessed** in this conversation  
✅ **Project** being worked on  
✅ **User preferences** from earlier messages  

### What Agent Forgets

❌ **Other conversations** (different threads)  
❌ **Sessions before restart** (unless saved to DB)  
❌ **Personal info** not in current thread  
❌ **Conversations in other channels** (isolated)  

---

## 💡 Best Practices

### 1. Keep Conversations Focused

**Good:**
```
Thread 1: "Fix authentication bug"
Thread 2: "Add new endpoint"
Thread 3: "Update documentation"
```

**Bad:**
```
Thread 1: "Fix auth, add endpoint, update docs, refactor..."
(Too much in one conversation, confusing context)
```

### 2. Use Threads Effectively

**In Slack:**
- New topic → New thread (new @mention in channel)
- Continue topic → Reply in thread
- Related follow-up → Same thread

**In Admin Panel:**
- Related questions → Same session
- New project → Refresh page
- Different topic → Start fresh test

### 3. Provide Context When Needed

**Less Effective:**
```
User: "Fix the bug"
Agent: "Which bug? Please provide more context."
```

**More Effective:**
```
User: "Fix the authentication timeout bug in auth.py line 45"
Agent: [Has clear context] "Looking at auth.py..."
```

### 4. Reference Earlier Messages

```
User: "Remember that file you showed me earlier?"
Agent: [Looks back in conversation history]
       "Yes, you're referring to config.py from 5 messages ago..."
```

---

## 🐛 Troubleshooting

### Agent Doesn't Remember Previous Messages

**Problem:** Agent acts like conversation is new

**Solutions:**
1. Verify conversation is saved to database
2. Check state_json contains message history
3. Ensure thread_ts is consistent
4. Look for errors in backend logs
5. Confirm database connection is working

```powershell
# Check conversation exists
docker-compose exec db psql -U postgres -d slack_cline \
  -c "SELECT message_count FROM conversations WHERE thread_ts='<thread_ts>';"
```

### Conversation State Not Persisting

**Problem:** Restart clears conversation history

**Solutions:**
1. Check PostgreSQL is running
2. Verify DATABASE_URL is correct
3. Ensure state is being saved after each message
4. Check for serialization errors in logs
5. Confirm transactions are committing

### "Conversation not found" Error

**Problem:** Agent can't find existing conversation

**Solutions:**
1. Verify channel_id and thread_ts are correct
2. Check database for conversation record
3. Ensure UNIQUE constraint isn't violated
4. Look for typos in conversation key
5. Confirm database migrations ran

---

## 📊 Monitoring Conversations

### Key Metrics

**Conversation Length:**
```sql
SELECT 
    AVG(message_count) as avg_messages,
    MAX(message_count) as max_messages
FROM conversations;
```

**Active Conversations:**
```sql
SELECT COUNT(*) 
FROM conversations 
WHERE updated_at > NOW() - INTERVAL '1 hour';
```

**Conversation Duration:**
```sql
SELECT 
    AVG(updated_at - created_at) as avg_duration
FROM conversations;
```

---

## 🚀 Advanced Features

### Conversation Branching (Future)

Create branches from existing conversations:

```
Main conversation: "Implement auth system"
├─ Branch 1: "Add OAuth support"
├─ Branch 2: "Add 2FA"
└─ Branch 3: "Add session management"
```

### Conversation Search (Future)

Search across all conversations:

```
User: "Find conversations about database migrations"
Agent: [Searches all conversation histories]
       "Found 3 conversations:
        1. 'Add users table' (2 days ago)
        2. 'Fix migration rollback' (1 week ago)
        3. 'Database schema design' (2 weeks ago)"
```

### Conversation Export (Future)

Export conversation history for:
- Documentation
- Training examples
- Team knowledge base
- Post-mortem analysis

---

## 🔗 Related Documentation

- **[Dashboard Guide](dashboard.md)** - Test conversations via Admin Panel
- **[Architecture Overview](../architecture/overview.md)** - Technical deep dive
- **[Agent System](../architecture/agent-system.md)** - How LangGraph processes conversations

---

## 📚 Comparison Table

| Feature | Run Model (Old) | Conversation Model (New) |
|---------|----------------|-------------------------|
| **Memory** | None | Full history |
| **State** | Ephemeral | Persistent |
| **Interface** | CLI commands | Slack threads |
| **Context** | Single request | Multi-turn |
| **Storage** | RunModel table | ConversationModel table |
| **Interaction** | Task-based | Conversational |
| **Tool Use** | Explicit commands | Autonomous |
| **Recovery** | Lost on restart | Survives restarts |

---

**Questions?** Open an issue on [GitHub](https://github.com/your-org/sline/issues) or check the architecture docs.

**Ready to test?** → [Admin Panel Guide](dashboard.md#admin-panel)
