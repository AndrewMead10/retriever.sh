import { useState } from 'react'
import { createFileRoute, redirect } from '@tanstack/react-router'
import { toast } from 'sonner'
import { Check, Copy } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { api, useCreateManagementKey, useManagementKeys, useRevokeManagementKey } from '@/lib/api'
import type { ManagementApiKeyCreateResponse } from '@/lib/types'
import { hasActiveSession } from '@/lib/session'
import { queryClient } from '@/routes/__root'

export const Route = createFileRoute('/api-keys')({
  beforeLoad: async () => {
    if (!hasActiveSession()) {
      throw redirect({ to: '/auth/login', search: { redirect: undefined } })
    }
    try {
      await queryClient.ensureQueryData({
        queryKey: ['user'],
        queryFn: api.auth.getCurrentUser,
      })
    } catch {
      throw redirect({ to: '/auth/login', search: { redirect: undefined } })
    }
  },
  component: ApiKeysPage,
})

type ExpirationChoice = '30' | '90' | '365' | 'never'

function ApiKeysPage() {
  const { data, isLoading, error } = useManagementKeys()
  const createKey = useCreateManagementKey()
  const revokeKey = useRevokeManagementKey()
  const [showCreate, setShowCreate] = useState(false)
  const [name, setName] = useState('Agent setup key')
  const [expires, setExpires] = useState<ExpirationChoice>('90')
  const [revealed, setRevealed] = useState<ManagementApiKeyCreateResponse | null>(null)
  const [copied, setCopied] = useState<string | null>(null)

  const baseUrl = typeof window !== 'undefined' ? window.location.origin : 'https://retriever.sh'

  const copyText = async (label: string, value: string) => {
    try {
      await navigator.clipboard.writeText(value)
      toast.success(`${label} copied to clipboard.`)
    } catch {
      toast(label, { description: value })
    }
    setCopied(label)
    setTimeout(() => setCopied(null), 2000)
  }

  const handleCreate = async () => {
    try {
      const result = await createKey.mutateAsync({
        name,
        expires_in_days: expires === 'never' ? null : Number(expires),
      })
      setShowCreate(false)
      setRevealed(result)
      await copyText('Management API key', result.api_key)
    } catch (err: any) {
      toast.error(err?.message || 'Failed to create management API key')
    }
  }

  const handleRevoke = (keyId: number) => {
    revokeKey.mutate(keyId, {
      onSuccess: () => toast.success('Management API key revoked.'),
      onError: (err: any) => toast.error(err?.message || 'Failed to revoke management API key'),
    })
  }

  if (isLoading) {
    return <div className="max-w-7xl mx-auto py-10 px-4">Loading API keys...</div>
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto py-10 px-4 text-red-600">
        Failed to load API keys: {String((error as any)?.message || 'Unknown error')}
      </div>
    )
  }

  const createProjectCurl = revealed
    ? `curl -X POST ${baseUrl}/api/projects \\
  -H "Authorization: Bearer ${revealed.api_key}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "Agent project",
    "description": "Created programmatically",
    "api_key_name": "agent-runtime-key",
    "api_key_expires_in_days": 90
  }'`
    : ''

  const createProjectKeyCurl = revealed
    ? `curl -X POST ${baseUrl}/api/projects/<project_id>/api-keys \\
  -H "Authorization: Bearer ${revealed.api_key}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "agent-runtime-key",
    "expires_in_days": 90
  }'`
    : ''

  return (
    <div className="min-h-screen bg-background dither-bg font-mono-jetbrains">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 space-y-8">
        <div className="flex items-center justify-between gap-6">
          <div className="space-y-4">
            <h1 className="text-4xl font-black dither-text leading-none">API KEYS</h1>
            <div className="h-1 bg-foreground dither-border"></div>
            <p className="text-lg text-muted-foreground font-mono-jetbrains leading-relaxed">
              Create management keys for agents that need to create projects and mint project API keys.
            </p>
          </div>
          <Dialog open={showCreate} onOpenChange={setShowCreate}>
            <DialogTrigger asChild>
              <Button className="bg-foreground text-background border-2 border-foreground sharp-corners font-bold hover:bg-muted hover:text-foreground">
                [ NEW MANAGEMENT KEY ]
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-transparent border-none p-0 [&_[data-slot=dialog-close]]:top-6 [&_[data-slot=dialog-close]]:right-6">
              <div className="bg-card border-2 border-foreground dither-border sharp-corners p-6">
                <DialogHeader>
                  <DialogTitle className="font-bold dither-text">NEW MANAGEMENT KEY</DialogTitle>
                </DialogHeader>
                <div className="space-y-4 py-2">
                  <div className="space-y-2">
                    <Label htmlFor="management-key-name" className="font-bold text-xs">// NAME</Label>
                    <Input
                      id="management-key-name"
                      value={name}
                      onChange={(event) => setName(event.target.value)}
                      className="bg-background border border-foreground dither-border sharp-corners"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="font-bold text-xs">// EXPIRES</Label>
                    <Select value={expires} onValueChange={(value) => setExpires(value as ExpirationChoice)}>
                      <SelectTrigger className="bg-background border border-foreground dither-border sharp-corners">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="30">30 days</SelectItem>
                        <SelectItem value="90">90 days</SelectItem>
                        <SelectItem value="365">1 year</SelectItem>
                        <SelectItem value="never">Never</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <p className="text-xs text-muted-foreground font-mono-jetbrains">
                    Management keys can create projects and mint project keys. Store them like production credentials.
                  </p>
                </div>
                <DialogFooter>
                  <Button
                    variant="outline"
                    onClick={() => setShowCreate(false)}
                    className="bg-background border-2 border-foreground text-foreground sharp-corners font-bold hover:bg-foreground hover:text-background"
                  >
                    [ CANCEL ]
                  </Button>
                  <Button
                    onClick={handleCreate}
                    disabled={!name.trim() || createKey.isPending}
                    className="bg-foreground text-background border-2 border-foreground sharp-corners font-bold hover:bg-muted hover:text-foreground disabled:opacity-50"
                  >
                    {createKey.isPending ? 'CREATING...' : '[ CREATE KEY ]'}
                  </Button>
                </DialogFooter>
              </div>
            </DialogContent>
          </Dialog>
        </div>

        <Card className="bg-card border-2 border-foreground dither-border sharp-corners">
          <CardHeader className="space-y-2">
            <CardTitle className="font-bold dither-text">MANAGEMENT KEYS</CardTitle>
            <CardDescription className="font-mono-jetbrains text-sm">
              These keys are account-level credentials for agent setup flows. Project API keys are still used for RAG ingest/query/delete.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {(data?.keys ?? []).length === 0 ? (
              <div className="text-sm text-muted-foreground font-mono-jetbrains bg-background border border-foreground dither-border sharp-corners p-4">
                No management keys yet.
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow className="border-b border-foreground">
                    <TableHead className="font-bold text-xs">// NAME</TableHead>
                    <TableHead className="font-bold text-xs">// PREFIX</TableHead>
                    <TableHead className="font-bold text-xs">// LAST USED</TableHead>
                    <TableHead className="font-bold text-xs">// EXPIRES</TableHead>
                    <TableHead className="font-bold text-xs text-right">// ACTIONS</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(data?.keys ?? []).map((key) => (
                    <TableRow key={key.id} className="border-b border-foreground/20">
                      <TableCell className="font-bold">{key.name}</TableCell>
                      <TableCell className="font-mono-jetbrains">{key.prefix}</TableCell>
                      <TableCell className="font-mono-jetbrains">{formatDate(key.last_used_at)}</TableCell>
                      <TableCell className="font-mono-jetbrains">{formatDate(key.expires_at)}</TableCell>
                      <TableCell className="text-right">
                        {key.revoked ? (
                          <span className="text-xs font-bold text-red-600">REVOKED</span>
                        ) : (
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => handleRevoke(key.id)}
                            disabled={revokeKey.isPending}
                            className="bg-red-600 text-white border-2 border-red-600 sharp-corners font-bold hover:bg-red-700"
                          >
                            [ REVOKE ]
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <Dialog open={revealed !== null} onOpenChange={(open) => !open && setRevealed(null)}>
          {revealed && (
            <DialogContent className="bg-transparent border-none p-0 [&_[data-slot=dialog-close]]:top-6 [&_[data-slot=dialog-close]]:right-6">
              <div className="bg-card border-2 border-foreground dither-border sharp-corners p-6">
                <DialogHeader>
                  <DialogTitle className="font-bold dither-text">MANAGEMENT KEY CREATED</DialogTitle>
                </DialogHeader>
                <div className="space-y-4 py-2">
                  <p className="text-sm font-mono-jetbrains">
                    This is the only time we will display this management key.
                  </p>
                  <CopyBlock
                    title="// MANAGEMENT API KEY"
                    value={revealed.api_key}
                    copied={copied === 'Management API key'}
                    onCopy={() => copyText('Management API key', revealed.api_key)}
                  />
                  <CopyBlock
                    title="// CREATE PROJECT + PROJECT KEY"
                    value={createProjectCurl}
                    copied={copied === 'Create project cURL'}
                    onCopy={() => copyText('Create project cURL', createProjectCurl)}
                  />
                  <CopyBlock
                    title="// MINT PROJECT KEY"
                    value={createProjectKeyCurl}
                    copied={copied === 'Mint project key cURL'}
                    onCopy={() => copyText('Mint project key cURL', createProjectKeyCurl)}
                  />
                </div>
                <DialogFooter>
                  <Button
                    onClick={() => setRevealed(null)}
                    className="bg-foreground text-background border-2 border-foreground sharp-corners font-bold hover:bg-muted hover:text-foreground"
                  >
                    [ CLOSE ]
                  </Button>
                </DialogFooter>
              </div>
            </DialogContent>
          )}
        </Dialog>
      </div>
    </div>
  )
}

function CopyBlock({
  title,
  value,
  copied,
  onCopy,
}: {
  title: string
  value: string
  copied: boolean
  onCopy: () => void
}) {
  return (
    <div className="space-y-2">
      <div className="text-xs font-bold text-muted-foreground">{title}</div>
      <div className="bg-background border-2 border-foreground dither-border sharp-corners p-3 space-y-3">
        <pre className="whitespace-pre-wrap break-all font-mono-jetbrains text-xs">{value}</pre>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onCopy}
          className="bg-background border border-foreground sharp-corners font-bold"
        >
          {copied ? <Check className="mr-2 h-3 w-3" /> : <Copy className="mr-2 h-3 w-3" />}
          {copied ? '[ COPIED ]' : '[ COPY ]'}
        </Button>
      </div>
    </div>
  )
}

function formatDate(value?: string | null) {
  if (!value) return 'Never'
  return new Date(value).toLocaleDateString()
}
