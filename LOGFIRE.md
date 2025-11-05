# LogFire Integration

This application includes Pydantic LogFire for structured logging and observability. LogFire provides automatic instrumentation for FastAPI and SQLAlchemy, giving you detailed insights into your RAG application's performance and behavior.

## Quick Start

### 1. Installation

LogFire is already included in the project dependencies. If you need to install it manually:

```bash
cd backend
uv sync  # This will install logfire
```

### 2. Configuration

Add the following to your `.env` file:

```bash
# Enable LogFire (default: true)
LOGFIRE_ENABLED=true

# Environment: development, staging, or production
LOGFIRE_ENVIRONMENT=development

# Service name for identification in logs
LOGFIRE_SERVICE_NAME=rag-app

# Optional: Send to external LogFire service (for production)
LOGFIRE_TOKEN=your-logfire-token-here
```

### 3. Development Usage

In development, LogFire will output structured logs to your console with detailed information about:

- **HTTP Requests**: All API calls with timing, status codes, and parameters
- **Database Queries**: SQLAlchemy queries with execution time and parameters
- **Custom Events**: Application-specific events like RAG queries

## Automatic Instrumentation

### FastAPI Integration

All HTTP endpoints are automatically instrumented. You'll see logs like:

```
INFO  HTTP request started
├─ method: POST
├─ path: /api/rag/projects/123/query
├─ remote_addr: 127.0.0.1
└─ user_agent: curl/7.68.0

INFO  HTTP request completed
├─ status_code: 200
├─ duration_ms: 245
└─ response_size: 1024
```

### SQLAlchemy Integration

All database queries are automatically logged:

```
INFO  Database query executed
├─ duration_ms: 12
├─ rows_returned: 5
├─ sql: SELECT * FROM projects WHERE id = ?
└─ parameters: [123]
```

## Custom Logging

### Adding LogFire to Your Code

```python
from ..config import settings
if settings.logfire_enabled:
    import logfire

# Simple structured logging
logfire.info("User action completed", user_id=123, action="login")

# Error logging with context
try:
    await process_rag_query(query)
except Exception as e:
    logfire.error("RAG processing failed",
                  error=str(e),
                  query=query[:100],  # Truncate for privacy
                  user_id=user.id)

# Custom spans for tracing operations
with logfire.span("RAG query processing"):
    embedding = await generate_embeddings(query)
    docs = await vector_search(embedding)
    response = await generate_response(query, docs)
    logfire.info("RAG pipeline completed",
                 document_count=len(docs),
                 response_length=len(response))
```

### Example in RAG API

The `/api/rag/projects/{project_id}/query` endpoint already includes LogFire logging:

```python
# Query start
logfire.info("RAG query started", {
    "project_id": project_id,
    "query_length": len(payload.query),
    "top_k": payload.top_k,
})

# ... query processing ...

# Query completion
logfire.info("RAG query completed successfully", {
    "project_id": project_id,
    "result_count": len(results),
    "account_id": account.id,
})
```

## Environment-Specific Behavior

### Development (`LOGFIRE_ENVIRONMENT=development`)

- Logs are output to console in a readable format
- No external service connection required
- Verbose logging for debugging

### Production (`LOGFIRE_ENVIRONMENT=production`)

- Structured JSON logs
- Requires `LOGFIRE_TOKEN` to send to external service
- Optimized for log aggregation systems

## LogFire Dashboard (Optional)

If you want to use the external LogFire service:

1. Sign up at [logfire.pydantic.dev](https://logfire.pydantic.dev)
2. Create a new project and get your API token
3. Set `LOGFIRE_TOKEN` in your `.env` file
4. Set `LOGFIRE_ENVIRONMENT=production`

This gives you:
- Real-time dashboard
- Log search and filtering
- Performance metrics and analytics
- Alerting capabilities

## Troubleshooting

### LogFire Not Working

1. Check that `LOGFIRE_ENABLED=true` in your environment
2. Ensure LogFire is installed: `uv sync`
3. Check that your `.env` file is in the project root

### No Logs Appearing

1. Verify the application is starting correctly
2. Check the console output for any LogFire initialization messages
3. Ensure requests are being made to your FastAPI application

### External Service Issues

1. Verify your `LOGFIRE_TOKEN` is correct
2. Check network connectivity to logfire.pydantic.dev
3. Confirm `LOGFIRE_ENVIRONMENT=production`

## Best Practices

1. **Structured Data**: Always use dictionaries for metadata to make logs searchable
2. **Privacy**: Don't log sensitive data like passwords, full query texts, or personal information
3. **Performance**: Use spans for expensive operations to track performance
4. **Error Context**: Include relevant context when logging errors (user_id, project_id, etc.)
5. **Consistency**: Use consistent field names across your logs for better analysis

## Example Logs

### Successful RAG Query
```json
{
  "timestamp": "2024-01-15T10:30:45Z",
  "level": "info",
  "message": "RAG query completed successfully",
  "data": {
    "project_id": 123,
    "result_count": 5,
    "account_id": 456
  }
}
```

### Error with Context
```json
{
  "timestamp": "2024-01-15T10:31:12Z",
  "level": "error",
  "message": "Database connection failed",
  "data": {
    "error": "Connection timeout",
    "user_id": 789,
    "operation": "create_project"
  }
}
```

For more information about LogFire, visit the [official documentation](https://docs.pydantic.dev/logfire/).