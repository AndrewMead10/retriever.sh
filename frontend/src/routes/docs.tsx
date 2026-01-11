import { createFileRoute } from '@tanstack/react-router'
import { useState, useEffect } from 'react'
import { Download, ChevronUp, Link } from 'lucide-react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { toast } from 'sonner'

export const Route = createFileRoute('/docs')({
  component: DocsPage,
})

type Language = 'python' | 'javascript' | 'curl'

function DocsPage() {
  const [selectedLanguage, setSelectedLanguage] = useState<Language>('python')
  const [showBackToTop, setShowBackToTop] = useState(false)

  useEffect(() => {
    const handleScroll = () => {
      setShowBackToTop(window.scrollY > 400)
    }

    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handleDownloadSkill = () => {
    const a = document.createElement('a')
    a.href = '/retriever-claude-skill.md'
    a.download = 'retriever-claude-skill.md'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

  const copyLinkToSection = (sectionId: string) => {
    const url = `${window.location.origin}${window.location.pathname}#${sectionId}`
    navigator.clipboard.writeText(url)
    toast.success('Link copied to clipboard!')
  }

  const CodeBlock = ({ code, language }: { code: string; language: string }) => (
    <div className="bg-background border border-foreground overflow-hidden sharp-corners">
      <SyntaxHighlighter
        language={language === 'curl' ? 'bash' : language}
        style={vscDarkPlus}
        customStyle={{
          margin: 0,
          padding: '1rem',
          background: 'transparent',
          fontSize: '0.875rem',
        }}
        codeTagProps={{
          style: {
            fontFamily: 'var(--font-mono-jetbrains), monospace',
          }
        }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  )

  const LanguageSwitcher = () => (
    <div className="flex gap-2 mb-6">
      <button
        onClick={() => setSelectedLanguage('python')}
        className={`px-4 py-2 font-mono text-sm border-2 border-foreground sharp-corners transition-colors ${
          selectedLanguage === 'python'
            ? 'bg-foreground text-background'
            : 'bg-background text-foreground hover:bg-muted'
        }`}
      >
        Python
      </button>
      <button
        onClick={() => setSelectedLanguage('javascript')}
        className={`px-4 py-2 font-mono text-sm border-2 border-foreground sharp-corners transition-colors ${
          selectedLanguage === 'javascript'
            ? 'bg-foreground text-background'
            : 'bg-background text-foreground hover:bg-muted'
        }`}
      >
        JavaScript
      </button>
      <button
        onClick={() => setSelectedLanguage('curl')}
        className={`px-4 py-2 font-mono text-sm border-2 border-foreground sharp-corners transition-colors ${
          selectedLanguage === 'curl'
            ? 'bg-foreground text-background'
            : 'bg-background text-foreground hover:bg-muted'
        }`}
      >
        cURL
      </button>
    </div>
  )

  const codeExamples = {
    ingest: {
      python: `import requests

def ingest_document(project_id: str, api_key: str, payload: dict):
    """Ingest a document into a project"""
    response = requests.post(
        f"https://retriever.sh/api/rag/projects/{project_id}/documents",
        headers={
            "X-Project-Key": api_key,
            "Content-Type": "application/json"
        },
        json=payload,
    )
    response.raise_for_status()
    return response.json()

# Usage
document = {
    "title": "Python Installation Guide",
    "text": "To install Python, visit python.org...",
    "metadata": {
        "source": "https://python.org/downloads/",
        "category": "docs"
    }
}
result = ingest_document("your-project-uuid", "proj_...your_key...", document)
print(f"Document ID: {result['id']}")`,
      javascript: `async function ingestDocument(projectId, apiKey, payload) {
  // Ingest a document into a project
  const response = await fetch(
    \`/api/rag/projects/\${projectId}/documents\`,
    {
      method: 'POST',
      headers: {
        'X-Project-Key': apiKey,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    }
  );
  if (!response.ok) {
    throw new Error('Failed to ingest document');
  }
  return await response.json();
}

// Usage
const document = {
  title: 'Python Installation Guide',
  text: 'To install Python, visit python.org...',
  metadata: {
    source: 'https://python.org/downloads/',
    category: 'docs'
  }
};
const result = await ingestDocument('your-project-uuid', 'proj_...your_key...', document);
console.log('Document ID:', result.id);`,
      curl: `# Ingest a document into a project
curl -X POST https://retriever.sh/api/rag/projects/your-project-uuid/documents \\
  -H "X-Project-Key: proj_...your_key..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "title": "Python Installation Guide",
    "text": "To install Python, visit python.org...",
    "metadata": {
      "source": "https://python.org/downloads/",
      "category": "docs"
    }
  }'`,
    },
    query: {
      python: `import requests

def query_project(project_id: str, api_key: str, query: str, top_k: int = 5):
    """Query a project using hybrid retrieval"""
    response = requests.post(
        f"https://retriever.sh/api/rag/projects/{project_id}/query",
        headers={
            "X-Project-Key": api_key,
            "Content-Type": "application/json"
        },
        json={"query": query, "top_k": top_k},
    )
    response.raise_for_status()
    return response.json()

# Usage
results = query_project("your-project-uuid", "proj_...your_key...", "How do I install Python?", top_k=5)
for result in results["results"]:
    print(f"{result['title']}: {result['content'][:120]}...")`,
      javascript: `async function queryProject(projectId, apiKey, payload) {
  // Query a project using hybrid retrieval
  const response = await fetch(
    \`/api/rag/projects/\${projectId}/query\`,
    {
      method: 'POST',
      headers: {
        'X-Project-Key': apiKey,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    }
  );
  if (!response.ok) {
    throw new Error('Failed to query project');
  }
  return await response.json();
}

// Usage
const results = await queryProject('your-project-uuid', 'proj_...your_key...', {
  query: 'How do I install Python?',
  top_k: 5,
  vector_k: 40
});
results.results.forEach(result => {
  console.log(\`\${result.title}: \${result.content.slice(0, 120)}...\`);
});`,
      curl: `# Query a project using hybrid retrieval
curl -X POST https://retriever.sh/api/rag/projects/your-project-uuid/query \\
  -H "X-Project-Key: proj_...your_key..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "query": "How do I install Python?",
    "top_k": 5,
    "vector_k": 40
  }'`,
    },
    delete: {
      python: `import requests

def delete_vector(project_id: str, document_id: int, api_key: str) -> None:
    """Delete a document vector from a project"""
    response = requests.delete(
        f"https://retriever.sh/api/rag/projects/{project_id}/vectors/{document_id}",
        headers={"X-Project-Key": api_key},
    )
    if response.status_code != 204:
        raise Exception(f"Delete failed: {response.text}")

# Usage
delete_vector("your-project-uuid", 456, "proj_...your_key...")`,
      javascript: `async function deleteVector(projectId, documentId, apiKey) {
  // Delete a document vector from a project
  const response = await fetch(
    \`/api/rag/projects/\${projectId}/vectors/\${documentId}\`,
    {
      method: 'DELETE',
      headers: { 'X-Project-Key': apiKey }
    }
  );
  if (response.status !== 204) {
    const message = await response.text();
    throw new Error(message || 'Failed to delete vector');
  }
}

// Usage
await deleteVector('your-project-uuid', 456, 'proj_...your_key...');`,
      curl: `# Delete a document vector from a project
curl -X DELETE https://retriever.sh/api/rag/projects/your-project-uuid/vectors/456 \\
  -H "X-Project-Key: proj_...your_key..."`,
    },
  }

  return (
    <div className="min-h-screen bg-background dither-bg font-mono-jetbrains">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        {/* Header */}
        <div className="text-center mb-16">
          <h1 className="text-6xl font-black dither-text mb-4">DOCUMENTATION</h1>
          <div className="h-1 bg-foreground w-32 mx-auto mb-6"></div>
          <p className="text-lg text-muted-foreground max-w-3xl mx-auto">
            Simple, powerful RAG API. Just three calls: ingest, query, delete.
          </p>
        </div>

        {/* Claude Code Skill Integration - Moved to top */}
        <div className="mb-16">
          <div className="bg-gradient-to-br from-primary/10 to-primary/5 border-2 border-primary dither-border sharp-corners p-8">
            <h2 className="text-3xl font-black dither-text mb-4">CLAUDE CODE SKILL</h2>
            <p className="text-muted-foreground mb-6">
              Enable Claude Code to automatically integrate retriever.sh into applications it builds for you. When you download this skill, Claude Code will know how to use the API for search functionality in your apps.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
              <div>
                <h3 className="text-xl font-bold mb-3">Quick Setup</h3>
                <div className="space-y-3">
                  <div>
                    <div className="text-sm text-muted-foreground mb-1">1. Download the skill file</div>
                    <button
                      onClick={handleDownloadSkill}
                      className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-foreground text-background border-2 border-foreground sharp-corners hover:bg-foreground/90 transition-colors"
                    >
                      <Download size={18} />
                      <span className="font-bold">Download Claude Code Skill</span>
                    </button>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground mb-1">2. Add to .claude/skills directory</div>
                    <div className="bg-background border border-foreground p-3 font-mono text-xs">
                      mv retriever-claude-skill.md .claude/skills/
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground mb-1">3. That's it!</div>
                    <div className="text-xs text-muted-foreground">
                      Claude Code will now automatically know how to integrate retriever.sh when building apps for you
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="text-xl font-bold mb-3">What It Does</h3>
                <ul className="space-y-2 text-muted-foreground">
                  <li className="flex items-start gap-2">
                    <span className="text-primary font-bold">•</span>
                    <span>Teaches Claude Code how to use the retriever.sh API</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-primary font-bold">•</span>
                    <span>Enables automatic integration into apps Claude builds</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-primary font-bold">•</span>
                    <span>Provides code examples and best practices</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-primary font-bold">•</span>
                    <span>Works seamlessly with all three core functions</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* Quick Start */}
        <div className="mb-16">
          <div className="bg-card border-2 border-foreground dither-border sharp-corners p-8">
            <h2 className="text-3xl font-black dither-text mb-6">// QUICK START</h2>
            <div className="space-y-6">
              <div>
                <h3 className="text-xl font-bold mb-3">1. Get Your API Key</h3>
                <p className="text-muted-foreground mb-4">
                  Create a project and copy its Project API key from the projects page. The Projects table also shows the project ID.
                </p>
                <div className="bg-background border border-foreground p-4 font-mono text-sm">
                  <div className="text-muted-foreground mb-2"># Example API key format</div>
                  <div>proj_51f8a9b2c3e4d5f6a7b8c9d0e1f2a3b4</div>
                </div>
              </div>

              <div>
                <h3 className="text-xl font-bold mb-3">2. Add the header</h3>
                <p className="text-muted-foreground">
                  Send the key as <span className="font-mono">X-Project-Key</span> and pass your project ID in the URL.
                  Local dev base URL: <span className="font-mono">https://retriever.sh</span>.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Three Core Functions */}
        <div className="mb-16">
          <h2 className="text-4xl font-black dither-text mb-8 text-center">THREE CORE ENDPOINTS</h2>
          <p className="text-center text-muted-foreground mb-8 max-w-2xl mx-auto">
            Everything you need to ingest content, query it, and remove it when needed.
          </p>

          <div className="space-y-8">
            {/* Ingest */}
            <div id="ingest" className="bg-card border-2 border-foreground dither-border sharp-corners p-8 scroll-mt-8">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h3 className="text-2xl font-black mb-2">1. INGEST DOCUMENT</h3>
                  <p className="text-muted-foreground">Store a document and its embedding for retrieval</p>
                </div>
                <div className="flex items-center gap-3">
                  <div className="bg-primary/10 border border-primary px-4 py-2 sharp-corners">
                    <span className="font-mono text-sm">POST /api/rag/projects/:project_id/documents</span>
                  </div>
                  <button
                    onClick={() => copyLinkToSection('ingest')}
                    className="p-2 border-2 border-foreground sharp-corners hover:bg-muted transition-colors"
                    aria-label="Copy link to Ingest section"
                  >
                    <Link size={16} />
                  </button>
                </div>
              </div>

              <LanguageSwitcher />

              <div className="mb-4">
                <h4 className="font-bold mb-3">Parameters</h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                  <div className="bg-background border border-foreground p-3">
                    <div className="font-mono mb-1">project_id</div>
                    <div className="text-muted-foreground text-xs">path param (required)</div>
                  </div>
                  <div className="bg-background border border-foreground p-3">
                    <div className="font-mono mb-1">X-Project-Key</div>
                    <div className="text-muted-foreground text-xs">header (required)</div>
                  </div>
                  <div className="bg-background border border-foreground p-3">
                    <div className="font-mono mb-1">body</div>
                    <div className="text-muted-foreground text-xs">DocumentIn (required)</div>
                  </div>
                </div>
              </div>

              <div className="mb-4">
                <h4 className="font-bold mb-3">Example</h4>
                <CodeBlock code={codeExamples.ingest[selectedLanguage]} language={selectedLanguage} />
              </div>

              <div>
                <h4 className="font-bold mb-3">Response (204 No Content)</h4>
                <div className="bg-background border border-foreground overflow-hidden sharp-corners">
                  <SyntaxHighlighter
                    language="json"
                    style={vscDarkPlus}
                    customStyle={{
                      margin: 0,
                      padding: '1rem',
                      background: 'transparent',
                      fontSize: '0.875rem',
                    }}
                  >
{`{
  "id": 456,
  "content": "To install Python, visit python.org...",
  "title": "Python Installation Guide",
  "metadata": {
    "source": "https://python.org/downloads/",
    "category": "docs"
  },
  "created_at": "2025-01-20T18:42:11.214Z"
}`}
                  </SyntaxHighlighter>
                </div>
              </div>
            </div>

            {/* Query */}
            <div id="query" className="bg-card border-2 border-foreground dither-border sharp-corners p-8 scroll-mt-8">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h3 className="text-2xl font-black mb-2">2. QUERY PROJECT</h3>
                  <p className="text-muted-foreground">Run hybrid search across your project</p>
                </div>
                <div className="flex items-center gap-3">
                  <div className="bg-primary/10 border border-primary px-4 py-2 sharp-corners">
                    <span className="font-mono text-sm">POST /api/rag/projects/:project_id/query</span>
                  </div>
                  <button
                    onClick={() => copyLinkToSection('query')}
                    className="p-2 border-2 border-foreground sharp-corners hover:bg-muted transition-colors"
                    aria-label="Copy link to Query section"
                  >
                    <Link size={16} />
                  </button>
                </div>
              </div>

              <LanguageSwitcher />

              <div className="mb-4">
                <h4 className="font-bold mb-3">Parameters</h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                  <div className="bg-background border border-foreground p-3">
                    <div className="font-mono mb-1">project_id</div>
                    <div className="text-muted-foreground text-xs">path param (required)</div>
                  </div>
                  <div className="bg-background border border-foreground p-3">
                    <div className="font-mono mb-1">X-Project-Key</div>
                    <div className="text-muted-foreground text-xs">header (required)</div>
                  </div>
                  <div className="bg-background border border-foreground p-3">
                    <div className="font-mono mb-1">query</div>
                    <div className="text-muted-foreground text-xs">string (required)</div>
                  </div>
                  <div className="bg-background border border-foreground p-3">
                    <div className="font-mono mb-1">top_k</div>
                    <div className="text-muted-foreground text-xs">integer (optional)</div>
                  </div>
                  <div className="bg-background border border-foreground p-3">
                    <div className="font-mono mb-1">vector_k</div>
                    <div className="text-muted-foreground text-xs">integer (optional)</div>
                  </div>
                </div>
              </div>

              <div className="mb-4">
                <h4 className="font-bold mb-3">Example</h4>
                <CodeBlock code={codeExamples.query[selectedLanguage]} language={selectedLanguage} />
              </div>

              <div>
                <h4 className="font-bold mb-3">Response</h4>
                <div className="bg-background border border-foreground overflow-hidden sharp-corners">
                  <SyntaxHighlighter
                    language="json"
                    style={vscDarkPlus}
                    customStyle={{
                      margin: 0,
                      padding: '1rem',
                      background: 'transparent',
                      fontSize: '0.875rem',
                    }}
                  >
{`{
  "results": [
    {
      "id": 456,
      "content": "To install Python, visit python.org...",
      "title": "Python Installation Guide",
      "metadata": {
        "source": "https://python.org/downloads/",
        "category": "docs"
      },
      "created_at": "2025-01-20T18:42:11.214Z"
    }
  ]
}`}
                  </SyntaxHighlighter>
                </div>
              </div>
            </div>

            {/* Delete */}
            <div id="delete" className="bg-card border-2 border-foreground dither-border sharp-corners p-8 scroll-mt-8">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h3 className="text-2xl font-black mb-2">3. DELETE VECTOR</h3>
                  <p className="text-muted-foreground">Remove a document vector by ID</p>
                </div>
                <div className="flex items-center gap-3">
                  <div className="bg-primary/10 border border-primary px-4 py-2 sharp-corners">
                    <span className="font-mono text-sm">DELETE /api/rag/projects/:project_id/vectors/:document_id</span>
                  </div>
                  <button
                    onClick={() => copyLinkToSection('delete')}
                    className="p-2 border-2 border-foreground sharp-corners hover:bg-muted transition-colors"
                    aria-label="Copy link to Delete section"
                  >
                    <Link size={16} />
                  </button>
                </div>
              </div>

              <LanguageSwitcher />

              <div className="mb-4">
                <h4 className="font-bold mb-3">Parameters</h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                  <div className="bg-background border border-foreground p-3">
                    <div className="font-mono mb-1">project_id</div>
                    <div className="text-muted-foreground text-xs">path param (required)</div>
                  </div>
                  <div className="bg-background border border-foreground p-3">
                    <div className="font-mono mb-1">document_id</div>
                    <div className="text-muted-foreground text-xs">path param (required)</div>
                  </div>
                  <div className="bg-background border border-foreground p-3">
                    <div className="font-mono mb-1">X-Project-Key</div>
                    <div className="text-muted-foreground text-xs">header (required)</div>
                  </div>
                </div>
              </div>

              <div className="mb-4">
                <h4 className="font-bold mb-3">Example</h4>
                <CodeBlock code={codeExamples.delete[selectedLanguage]} language={selectedLanguage} />
              </div>

              <div>
                <h4 className="font-bold mb-3">Response</h4>
                <div className="bg-background border border-foreground overflow-hidden sharp-corners">
                  <SyntaxHighlighter
                    language="json"
                    style={vscDarkPlus}
                    customStyle={{
                      margin: 0,
                      padding: '1rem',
                      background: 'transparent',
                      fontSize: '0.875rem',
                    }}
                  >
{`null`}
                  </SyntaxHighlighter>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Back to Top Button */}
        {showBackToTop && (
          <button
            onClick={scrollToTop}
            className="fixed bottom-8 right-8 bg-foreground text-background border-2 border-foreground p-3 rounded-full hover:bg-foreground/90 transition-all duration-300 shadow-lg z-50 flex items-center justify-center"
            aria-label="Back to top"
          >
            <ChevronUp size={20} />
          </button>
        )}
      </div>
    </div>
  )
}
