# Cline CLI Authentication Setup

This document explains how to configure API keys for Cline CLI to enable autonomous code execution in slack-cline.

## Overview

The slack-cline backend uses Cline CLI in subprocess mode to execute coding tasks. Each Cline instance requires authentication with an LLM provider (Anthropic, OpenAI, OpenRouter, etc.) before it can process tasks.

The system now supports **programmatic authentication** using the `cline auth` command with flags, eliminating the need for interactive setup wizards.

## Authentication Flow

When a run starts, the system:
1. Clones the repository to a workspace
2. Creates a new Cline instance (`cline instance new`)
3. **Configures authentication** (`cline auth --provider ... --apikey ... --modelid ...`)
4. Creates the task (`cline task new -y`)
5. Streams output and events

## Configuration

### Environment Variables

Add these variables to your `.env` file:

```bash
# Cline CLI Authentication Configuration
CLINE_PROVIDER=anthropic
CLINE_API_KEY=your_api_key_here
CLINE_MODEL_ID=claude-sonnet-4-5-20250929
CLINE_BASE_URL=  # Optional, only for openai-compatible providers
```

### Supported Providers

The following providers are supported for programmatic authentication:

| Provider | ID | Example Model ID | Requires Base URL |
|----------|----|--------------------|-------------------|
| Anthropic | `anthropic` | `claude-sonnet-4-5-20250929` | No |
| OpenAI Native | `openai-native` | `gpt-4o` | No |
| OpenAI Compatible | `openai` | `gpt-4` | Yes |
| OpenRouter | `openrouter` | `anthropic/claude-3.5-sonnet` | No |
| Google Gemini | `gemini` | `gemini-2.0-flash-exp` | No |
| xAI | `xai` | `grok-2-latest` | No |
| Cerebras | `cerebras` | `llama3.1-8b` | No |
| Ollama | `ollama` | `llama2` | No (uses base URL as API key) |

**Note:** Bedrock is NOT supported for programmatic authentication due to complex auth requirements. Use interactive setup if Bedrock is needed.

## Provider-Specific Configuration

### Anthropic (Recommended)

```bash
CLINE_PROVIDER=anthropic
CLINE_API_KEY=sk-ant-api03-xxxxxxxxxxxxx
CLINE_MODEL_ID=claude-sonnet-4-5-20250929
```

Get your API key from: https://console.anthropic.com/

### OpenAI Native

```bash
CLINE_PROVIDER=openai-native
CLINE_API_KEY=sk-xxxxxxxxxxxxx
CLINE_MODEL_ID=gpt-4o
```

Get your API key from: https://platform.openai.com/api-keys

### OpenRouter

```bash
CLINE_PROVIDER=openrouter
CLINE_API_KEY=sk-or-xxxxxxxxxxxxx
CLINE_MODEL_ID=anthropic/claude-3.5-sonnet
```

Get your API key from: https://openrouter.ai/keys

### OpenAI-Compatible (e.g., Azure OpenAI, LM Studio)

```bash
CLINE_PROVIDER=openai
CLINE_API_KEY=your_api_key
CLINE_MODEL_ID=gpt-4
CLINE_BASE_URL=https://your-endpoint.openai.azure.com/v1
```

### Ollama (Local)

```bash
CLINE_PROVIDER=ollama
CLINE_API_KEY=http://localhost:11434  # Base URL goes in API key field
CLINE_MODEL_ID=llama2
```

Ensure Ollama is running locally or update the URL to your Ollama server.

## Implementation Details

### CLI Client (`cli_client.py`)

The `ClineCliClient` class now includes authentication configuration:

```python
async def _configure_auth(
    self,
    instance_address: str,
    workspace_path: str,
    provider: str,
    api_key: str,
    model_id: str,
    base_url: Optional[str] = None
) -> None:
    """Configure authentication for a Cline instance."""
    cmd = [
        "cline", "auth",
        "--provider", provider,
        "--apikey", api_key,
        "--modelid", model_id,
        "--address", instance_address,
        "--output-format", "json"
    ]
    
    if base_url:
        cmd.extend(["--baseurl", base_url])
    
    # Execute command...
```

### Configuration (`config.py`)

New Pydantic settings for authentication:

```python
class Settings(BaseSettings):
    # ...existing settings...
    
    # Cline CLI authentication settings
    cline_provider: str = Field(default="anthropic")
    cline_api_key: str = Field(default="")
    cline_model_id: str = Field(default="claude-sonnet-4-5-20250929")
    cline_base_url: str = Field(default="")
```

### Orchestrator Integration

The orchestrator passes credentials to the CLI client:

```python
result = await self.cli_client.start_run(
    repo_url=project.repo_url,
    ref_type="branch",
    ref=project.default_ref,
    prompt=command.task_prompt,
    provider=settings.cline_provider,
    api_key=settings.cline_api_key,
    model_id=settings.cline_model_id,
    base_url=settings.cline_base_url or None
)
```

## JSON Output Format

All Cline CLI commands now use `--output-format json` for reliable parsing:

- `cline instance new --output-format json` → Returns instance address
- `cline auth --output-format json` → Returns auth confirmation
- `cline task new --output-format json` → Returns task ID

This ensures robust error handling and forward compatibility.

## Testing Authentication

To test authentication manually:

```bash
# Start a Cline instance
cline instance new --output-format json

# Configure auth (replace with your actual credentials)
cline auth \
  --provider anthropic \
  --apikey sk-ant-xxxxx \
  --modelid claude-sonnet-4-5-20250929 \
  --address localhost:50052 \
  --output-format json

# Create a test task
cline task new \
  --yolo \
  --address localhost:50052 \
  --output-format json \
  "Create a simple hello world Python script"

# View task output
cline task view \
  --follow-complete \
  --address localhost:50052
```

## Security Considerations

### API Key Storage

- **Environment Variables**: Keys are stored in `.env` file (gitignored)
- **Never commit**: Ensure `.env` is in `.gitignore`
- **Production**: Use secrets management (AWS Secrets Manager, HashiCorp Vault, etc.)

### Future: Database Storage

For multi-tenant support, API keys should be:
1. Encrypted at rest (AES-256)
2. Stored per tenant in database
3. Retrieved only when needed
4. Never logged or exposed in errors

## Troubleshooting

### "Failed to configure authentication"

**Symptoms**: Run fails immediately after instance creation

**Causes**:
- Invalid API key
- Invalid provider ID
- Invalid model ID
- Network issues

**Solutions**:
1. Verify API key is correct and has not expired
2. Check provider ID matches supported providers list
3. Ensure model ID exists for the provider
4. Test API key manually with `curl` or provider CLI

### "No instance address found in JSON response"

**Symptoms**: Run fails at instance creation

**Causes**:
- Cline CLI version mismatch
- JSON parsing failure

**Solutions**:
1. Update Cline CLI: `npm update -g cline`
2. Check CLI version: `cline --version`
3. Enable verbose logging: Set `DEBUG=true` in `.env`

### "Model validation failed"

**Symptoms**: Authentication succeeds but task creation fails

**Causes**:
- Model ID doesn't exist for provider
- Model requires special permissions

**Solutions**:
1. Verify model ID on provider's website
2. Check account has access to model
3. Try a different model from the same provider

## Future Enhancements

### Phase 1: MVP (Current)
- ✅ Environment variable configuration
- ✅ Single provider per deployment
- ✅ Programmatic authentication

### Phase 2: Multi-Tenant
- [ ] Database storage for API keys
- [ ] Per-tenant provider configuration
- [ ] API key encryption at rest
- [ ] Admin UI for key management

### Phase 3: Advanced
- [ ] Multiple providers per tenant
- [ ] Model fallback/retry logic
- [ ] Cost tracking and limits
- [ ] API key rotation

## References

- [Cline CLI Documentation](https://docs.cline.bot/cline-cli/)
- [Cline Auth Command](https://docs.cline.bot/cline-cli/commands#auth)
- [Provider Configuration Guide](https://docs.cline.bot/model-config/)
- [Supported Models List](https://docs.cline.bot/model-selection/)
