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
    search: {
      python: `import requests

def search(query: str, api_key: str, limit: int = 10):
    """Search your knowledge base"""
    response = requests.post(
        "https://api.retriever.sh/v1/search",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={"query": query, "limit": limit}
    )
    return response.json()

# Usage
results = search("How do I install Python?", "rs_live_...")
for result in results["results"]:
    print(f"{result['title']}: {result['content']}")`,
      javascript: `async function search(query, apiKey, limit = 10) {
  // Search your knowledge base
  const response = await fetch('https://api.retriever.sh/v1/search', {
    method: 'POST',
    headers: {
      'Authorization': \`Bearer \${apiKey}\`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ query, limit })
  });
  return await response.json();
}

// Usage
const results = await search('How do I install Python?', 'rs_live_...');
results.results.forEach(result => {
  console.log(\`\${result.title}: \${result.content}\`);
});`,
      curl: `# Search your knowledge base
curl -X POST https://api.retriever.sh/v1/search \\
  -H "Authorization: Bearer rs_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "query": "How do I install Python?",
    "limit": 10
  }'`,
    },
    add: {
      python: `import requests

def add_documents(documents: list, api_key: str):
    """Add documents to your knowledge base"""
    response = requests.post(
        "https://api.retriever.sh/v1/documents",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={"documents": documents}
    )
    return response.json()

# Usage
docs = [
    {
        "id": "doc_1",
        "title": "Python Installation Guide",
        "content": "To install Python, visit python.org...",
        "metadata": {"category": "tutorial"}
    }
]
result = add_documents(docs, "rs_live_...")
print(f"Added {result['count']} documents")`,
      javascript: `async function addDocuments(documents, apiKey) {
  // Add documents to your knowledge base
  const response = await fetch('https://api.retriever.sh/v1/documents', {
    method: 'POST',
    headers: {
      'Authorization': \`Bearer \${apiKey}\`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ documents })
  });
  return await response.json();
}

// Usage
const docs = [
  {
    id: 'doc_1',
    title: 'Python Installation Guide',
    content: 'To install Python, visit python.org...',
    metadata: { category: 'tutorial' }
  }
];
const result = await addDocuments(docs, 'rs_live_...');
console.log(\`Added \${result.count} documents\`);`,
      curl: `# Add documents to your knowledge base
curl -X POST https://api.retriever.sh/v1/documents \\
  -H "Authorization: Bearer rs_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "documents": [
      {
        "id": "doc_1",
        "title": "Python Installation Guide",
        "content": "To install Python, visit python.org...",
        "metadata": {"category": "tutorial"}
      }
    ]
  }'`,
    },
    delete: {
      python: `import requests

def delete_document(document_id: str, api_key: str):
    """Delete a document from your knowledge base"""
    response = requests.delete(
        f"https://api.retriever.sh/v1/documents/{document_id}",
        headers={"Authorization": f"Bearer {api_key}"}
    )
    return response.json()

# Usage
result = delete_document("doc_1", "rs_live_...")
print(f"Deleted: {result['success']}")`,
      javascript: `async function deleteDocument(documentId, apiKey) {
  // Delete a document from your knowledge base
  const response = await fetch(
    \`https://api.retriever.sh/v1/documents/\${documentId}\`,
    {
      method: 'DELETE',
      headers: { 'Authorization': \`Bearer \${apiKey}\` }
    }
  );
  return await response.json();
}

// Usage
const result = await deleteDocument('doc_1', 'rs_live_...');
console.log(\`Deleted: \${result.success}\`);`,
      curl: `# Delete a document from your knowledge base
curl -X DELETE https://api.retriever.sh/v1/documents/doc_1 \\
  -H "Authorization: Bearer rs_live_..."`,
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
            Simple, powerful search API. Just three functions: add, search, delete.
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
                  Sign up and retrieve your API key from the projects page.
                </p>
                <div className="bg-background border border-foreground p-4 font-mono text-sm">
                  <div className="text-muted-foreground mb-2"># Example API key format</div>
                  <div>rs_live_51f8a9b2c3e4d5f6a7b8c9d0e1f2a3b4</div>
                </div>
              </div>

              <div>
                <h3 className="text-xl font-bold mb-3">2. That's It!</h3>
                <p className="text-muted-foreground">
                  You're ready to use all three core functions: add documents, search your knowledge base, and delete when needed.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Three Core Functions */}
        <div className="mb-16">
          <h2 className="text-4xl font-black dither-text mb-8 text-center">THREE SIMPLE FUNCTIONS</h2>
          <p className="text-center text-muted-foreground mb-8 max-w-2xl mx-auto">
            Everything you need to build powerful search into your application. No complexity, just three essential operations.
          </p>

          <div className="space-y-8">
            {/* Search */}
            <div id="search" className="bg-card border-2 border-foreground dither-border sharp-corners p-8 scroll-mt-8">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h3 className="text-2xl font-black mb-2">1. SEARCH</h3>
                  <p className="text-muted-foreground">Find relevant documents using semantic search</p>
                </div>
                <div className="flex items-center gap-3">
                  <div className="bg-primary/10 border border-primary px-4 py-2 sharp-corners">
                    <span className="font-mono text-sm">POST /v1/search</span>
                  </div>
                  <button
                    onClick={() => copyLinkToSection('search')}
                    className="p-2 border-2 border-foreground sharp-corners hover:bg-muted transition-colors"
                    aria-label="Copy link to Search section"
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
                    <div className="font-mono mb-1">query</div>
                    <div className="text-muted-foreground text-xs">string (required)</div>
                  </div>
                  <div className="bg-background border border-foreground p-3">
                    <div className="font-mono mb-1">limit</div>
                    <div className="text-muted-foreground text-xs">integer (default: 10)</div>
                  </div>
                  <div className="bg-background border border-foreground p-3">
                    <div className="font-mono mb-1">metadata filters</div>
                    <div className="text-muted-foreground text-xs">object (optional)</div>
                  </div>
                </div>
              </div>

              <div className="mb-4">
                <h4 className="font-bold mb-3">Example</h4>
                <CodeBlock code={codeExamples.search[selectedLanguage]} language={selectedLanguage} />
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
      "id": "doc_123",
      "title": "Document Title",
      "content": "Relevant excerpt from the document...",
      "score": 0.95,
      "metadata": {
        "category": "tutorial",
        "author": "John Doe"
      }
    }
  ],
  "total": 1,
  "query_time": 0.045
}`}
                  </SyntaxHighlighter>
                </div>
              </div>
            </div>

            {/* Add */}
            <div id="add" className="bg-card border-2 border-foreground dither-border sharp-corners p-8 scroll-mt-8">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h3 className="text-2xl font-black mb-2">2. ADD</h3>
                  <p className="text-muted-foreground">Add documents to your knowledge base</p>
                </div>
                <div className="flex items-center gap-3">
                  <div className="bg-primary/10 border border-primary px-4 py-2 sharp-corners">
                    <span className="font-mono text-sm">POST /v1/documents</span>
                  </div>
                  <button
                    onClick={() => copyLinkToSection('add')}
                    className="p-2 border-2 border-foreground sharp-corners hover:bg-muted transition-colors"
                    aria-label="Copy link to Add section"
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
                    <div className="font-mono mb-1">documents</div>
                    <div className="text-muted-foreground text-xs">array (required)</div>
                  </div>
                  <div className="bg-background border border-foreground p-3">
                    <div className="font-mono mb-1">id</div>
                    <div className="text-muted-foreground text-xs">unique identifier</div>
                  </div>
                  <div className="bg-background border border-foreground p-3">
                    <div className="font-mono mb-1">metadata</div>
                    <div className="text-muted-foreground text-xs">custom fields</div>
                  </div>
                </div>
              </div>

              <div className="mb-4">
                <h4 className="font-bold mb-3">Example</h4>
                <CodeBlock code={codeExamples.add[selectedLanguage]} language={selectedLanguage} />
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
  "count": 1,
  "status": "success",
  "indexed_ids": ["doc_1"]
}`}
                  </SyntaxHighlighter>
                </div>
              </div>
            </div>

            {/* Delete */}
            <div id="delete" className="bg-card border-2 border-foreground dither-border sharp-corners p-8 scroll-mt-8">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h3 className="text-2xl font-black mb-2">3. DELETE</h3>
                  <p className="text-muted-foreground">Remove documents from your knowledge base</p>
                </div>
                <div className="flex items-center gap-3">
                  <div className="bg-primary/10 border border-primary px-4 py-2 sharp-corners">
                    <span className="font-mono text-sm">DELETE /v1/documents/:id</span>
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
                    <div className="font-mono mb-1">document_id</div>
                    <div className="text-muted-foreground text-xs">string (required)</div>
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
{`{
  "success": true,
  "deleted_id": "doc_1"
}`}
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
