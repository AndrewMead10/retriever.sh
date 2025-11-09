import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/docs')({
  component: DocsPage,
})

function DocsPage() {
  return (
    <div className="min-h-screen bg-background dither-bg font-mono-jetbrains">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-16">

        {/* Header */}
        <div className="text-center mb-16">
          <h1 className="text-6xl font-black dither-text mb-4">DOCUMENTATION</h1>
          <div className="h-1 bg-foreground w-32 mx-auto mb-6"></div>
          <p className="text-lg text-muted-foreground max-w-3xl mx-auto">
            Complete API reference and integration guides for the retriever.sh search API
          </p>
        </div>

        {/* Quick Start */}
        <div className="mb-16">
          <div className="bg-card border-2 border-foreground dither-border sharp-corners p-8">
            <h2 className="text-3xl font-black dither-text mb-6">// QUICK START</h2>
            <div className="space-y-6">
              <div>
                <h3 className="text-xl font-bold mb-3">1. Get Your API Key</h3>
                <p className="text-muted-foreground mb-4">
                  Sign up and retrieve your API key from the projects page.
                </p>
                <div className="bg-background border border-foreground p-4 font-mono text-sm">
                  <div className="text-muted-foreground mb-2"># Example API key format</div>
                  <div>rs_live_51f8a9b2c3e4d5f6a7b8c9d0e1f2a3b4</div>
                </div>
              </div>

              <div>
                <h3 className="text-xl font-bold mb-3">2. Make Your First Search</h3>
                <p className="text-muted-foreground mb-4">
                  Send a POST request to our search endpoint with your query.
                </p>
                <div className="bg-background border border-foreground p-4 font-mono text-sm overflow-x-auto">
                  <pre className="text-muted-foreground">
{`curl -X POST https://api.retriever.sh/v1/search \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "query": "your search terms",
    "limit": 10
  }'`}
                  </pre>
                </div>
              </div>

              <div>
                <h3 className="text-xl font-bold mb-3">3. Handle Response</h3>
                <p className="text-muted-foreground mb-4">
                  Process the search results and integrate them into your application.
                </p>
                <div className="bg-background border border-foreground p-4 font-mono text-sm overflow-x-auto">
                  <pre className="text-muted-foreground">
{`{
  "results": [
    {
      "id": "doc_123",
      "title": "Document Title",
      "content": "Relevant excerpt...",
      "score": 0.95,
      "metadata": {...}
    }
  ],
  "total": 1,
  "query_time": 0.045
}`}
                  </pre>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* API Reference */}
        <div className="mb-16">
          <h2 className="text-4xl font-black dither-text mb-8 text-center">API REFERENCE</h2>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Search Endpoint */}
            <div className="bg-card border-2 border-foreground dither-border sharp-corners p-6">
              <h3 className="text-xl font-black mb-4">POST /v1/search</h3>
              <div className="space-y-4">
                <div>
                  <h4 className="font-bold mb-2">Description</h4>
                  <p className="text-sm text-muted-foreground">
                    Search through your indexed documents using semantic and full-text search.
                  </p>
                </div>

                <div>
                  <h4 className="font-bold mb-2">Headers</h4>
                  <div className="bg-background border border-foreground p-3 font-mono text-xs">
                    <div>Authorization: Bearer YOUR_API_KEY</div>
                    <div>Content-Type: application/json</div>
                  </div>
                </div>

                <div>
                  <h4 className="font-bold mb-2">Body Parameters</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="font-mono">query</span>
                      <span className="text-muted-foreground">string (required)</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="font-mono">limit</span>
                      <span className="text-muted-foreground">integer (optional, default: 10)</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="font-mono">offset</span>
                      <span className="text-muted-foreground">integer (optional, default: 0)</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="font-mono">filters</span>
                      <span className="text-muted-foreground">object (optional)</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Index Endpoint */}
            <div className="bg-card border-2 border-foreground dither-border sharp-corners p-6">
              <h3 className="text-xl font-black mb-4">POST /v1/index</h3>
              <div className="space-y-4">
                <div>
                  <h4 className="font-bold mb-2">Description</h4>
                  <p className="text-sm text-muted-foreground">
                    Add or update documents in your search index.
                  </p>
                </div>

                <div>
                  <h4 className="font-bold mb-2">Headers</h4>
                  <div className="bg-background border border-foreground p-3 font-mono text-xs">
                    <div>Authorization: Bearer YOUR_API_KEY</div>
                    <div>Content-Type: application/json</div>
                  </div>
                </div>

                <div>
                  <h4 className="font-bold mb-2">Body Parameters</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="font-mono">documents</span>
                      <span className="text-muted-foreground">array (required)</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="font-mono">batch_id</span>
                      <span className="text-muted-foreground">string (optional)</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Claude Skill Integration */}
            <div className="bg-card border-2 border-foreground dither-border sharp-corners p-6">
              <h3 className="text-xl font-black mb-4">CLAUDE SKILL INTEGRATION</h3>
              <div className="space-y-4">
                <div>
                  <h4 className="font-bold mb-2">Skill Command</h4>
                  <div className="bg-background border border-foreground p-3 font-mono text-xs">
                    <div>/retriever-search your query here</div>
                  </div>
                </div>

                <div>
                  <h4 className="font-bold mb-2">Configuration</h4>
                  <p className="text-sm text-muted-foreground mb-2">
                    Add your retriever.sh API key to your Claude environment:
                  </p>
                  <div className="bg-background border border-foreground p-3 font-mono text-xs">
                    <div>RETRIEVER_API_KEY=rs_live_...</div>
                  </div>
                </div>

                <div>
                  <h4 className="font-bold mb-2">Features</h4>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    <li>• Automatic context retrieval</li>
                    <li>• Semantic search capabilities</li>
                    <li>• Real-time result integration</li>
                  </ul>
                </div>
              </div>
            </div>

            {/* Rate Limits */}
            <div className="bg-card border-2 border-foreground dither-border sharp-corners p-6">
              <h3 className="text-xl font-black mb-4">RATE LIMITS</h3>
              <div className="space-y-4">
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="font-bold">Tinkering Plan</span>
                    <span className="text-muted-foreground">10,000 queries/month</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="font-bold">Building Plan</span>
                    <span className="text-muted-foreground">100,000 queries/month</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="font-bold">Scale Plan</span>
                    <span className="text-muted-foreground">1M+ queries/month</span>
                  </div>
                </div>

                <div className="border-t border-foreground pt-4">
                  <h4 className="font-bold mb-2">Response Headers</h4>
                  <div className="bg-background border border-foreground p-3 font-mono text-xs">
                    <div>X-RateLimit-Limit: 10000</div>
                    <div>X-RateLimit-Remaining: 9999</div>
                    <div>X-RateLimit-Reset: 1640995200</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Code Examples */}
        <div className="mb-16">
          <h2 className="text-4xl font-black dither-text mb-8 text-center">CODE EXAMPLES</h2>

          <div className="space-y-8">
            {/* Python Example */}
            <div className="bg-card border-2 border-foreground dither-border sharp-corners p-6">
              <h3 className="text-xl font-black mb-4">Python</h3>
              <div className="bg-background border border-foreground p-4 font-mono text-sm overflow-x-auto">
                <pre className="text-muted-foreground">
{`import requests

def search_documents(query, api_key):
    url = "https://api.retriever.sh/v1/search"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "query": query,
        "limit": 10
    }

    response = requests.post(url, headers=headers, json=data)
    return response.json()

# Usage
results = search_documents("your search terms", "rs_live_...")
print(results["results"])`}
                </pre>
              </div>
            </div>

            {/* JavaScript Example */}
            <div className="bg-card border-2 border-foreground dither-border sharp-corners p-6">
              <h3 className="text-xl font-black mb-4">JavaScript / Node.js</h3>
              <div className="bg-background border border-foreground p-4 font-mono text-sm overflow-x-auto">
                <pre className="text-muted-foreground">
{`async function searchDocuments(query, apiKey) {
  const response = await fetch('https://api.retriever.sh/v1/search', {
    method: 'POST',
    headers: {
      'Authorization': \`Bearer \${apiKey}\`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      query: query,
      limit: 10
    })
  });

  return await response.json();
}

// Usage
const results = await searchDocuments('your search terms', 'rs_live_...');
console.log(results.results);`}
                </pre>
              </div>
            </div>

            {/* cURL Example */}
            <div className="bg-card border-2 border-foreground dither-border sharp-corners p-6">
              <h3 className="text-xl font-black mb-4">cURL</h3>
              <div className="bg-background border border-foreground p-4 font-mono text-sm overflow-x-auto">
                <pre className="text-muted-foreground">
{`# Basic search
curl -X POST https://api.retriever.sh/v1/search \\
  -H "Authorization: Bearer rs_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{"query": "your search terms"}'

# Search with filters
curl -X POST https://api.retriever.sh/v1/search \\
  -H "Authorization: Bearer rs_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "query": "your search terms",
    "filters": {
      "category": "documentation",
      "date_after": "2024-01-01"
    },
    "limit": 5
  }'`}
                </pre>
              </div>
            </div>
          </div>
        </div>

        {/* Error Handling */}
        <div className="mb-16">
          <h2 className="text-4xl font-black dither-text mb-8 text-center">ERROR HANDLING</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="bg-card border-2 border-foreground dither-border sharp-corners p-6">
              <h3 className="text-xl font-black mb-4">HTTP Status Codes</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="font-mono">200</span>
                  <span className="text-muted-foreground">Success</span>
                </div>
                <div className="flex justify-between">
                  <span className="font-mono">400</span>
                  <span className="text-muted-foreground">Bad Request</span>
                </div>
                <div className="flex justify-between">
                  <span className="font-mono">401</span>
                  <span className="text-muted-foreground">Unauthorized</span>
                </div>
                <div className="flex justify-between">
                  <span className="font-mono">429</span>
                  <span className="text-muted-foreground">Rate Limited</span>
                </div>
                <div className="flex justify-between">
                  <span className="font-mono">500</span>
                  <span className="text-muted-foreground">Internal Server Error</span>
                </div>
              </div>
            </div>

            <div className="bg-card border-2 border-foreground dither-border sharp-corners p-6">
              <h3 className="text-xl font-black mb-4">Error Response Format</h3>
              <div className="bg-background border border-foreground p-4 font-mono text-xs overflow-x-auto">
                <pre className="text-muted-foreground">
{`{
  "error": {
    "code": "INVALID_API_KEY",
    "message": "The provided API key is invalid",
    "request_id": "req_123456789"
  }
}`}
                </pre>
              </div>
            </div>
          </div>
        </div>

        {/* Support */}
        <div className="text-center">
          <div className="bg-card border-2 border-foreground dither-border sharp-corners p-8">
            <h2 className="text-3xl font-black dither-text mb-4">NEED HELP?</h2>
            <p className="text-muted-foreground mb-6">
              Questions about integration or need support? We're here to help.
            </p>
            <div className="space-y-2">
              <div className="text-sm">
                <span className="font-bold">Email:</span> support@retriever.sh
              </div>
              <div className="text-sm">
                <span className="font-bold">Discord:</span> discord.retriever.sh
              </div>
              <div className="text-sm">
                <span className="font-bold">Status:</span> status.retriever.sh
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
