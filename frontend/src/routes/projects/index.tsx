import { useState, type ReactNode } from 'react'
import { createFileRoute, redirect, Link } from '@tanstack/react-router'
import { useMutation } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Progress } from '@/components/ui/progress'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { api, useCreateProject, useDeleteProject, useProjects, useRotateProjectKey } from '@/lib/api'
import type { ProjectCreatePayload } from '@/lib/types'
import { queryClient } from '@/routes/__root'
import { formatNumber } from '@/utils/format'
import { hasActiveSession } from '@/lib/session'

export const Route = createFileRoute('/projects/')({
  beforeLoad: async () => {
    if (!hasActiveSession()) {
      throw redirect({ to: '/auth/login', search: { redirect: undefined } })
    }
    try {
      await queryClient.ensureQueryData({
        queryKey: ['user'],
        queryFn: api.auth.getCurrentUser,
      })
      await queryClient.ensureQueryData({
        queryKey: ['projects'],
        queryFn: api.projects.list,
      })
    } catch {
      throw redirect({ to: '/auth/login', search: { redirect: undefined } })
    }
  },
  component: ProjectsPage,
})

type ApiKeyRevealReason = 'create' | 'rotate'

type ApiKeyModalState =
  | { open: false }
  | { open: true; mode: 'confirm'; projectId: string; projectName: string }
  | { open: true; mode: 'reveal'; apiKey: string; projectId: string; projectName: string; reason: ApiKeyRevealReason }

function ProjectsPage() {
  const { data, isLoading, error } = useProjects()
  const createProject = useCreateProject()
  const deleteProject = useDeleteProject()
  const rotateProjectKey = useRotateProjectKey()
  const [showCreate, setShowCreate] = useState(false)
  const [formState, setFormState] = useState<ProjectCreatePayload>({
    name: '',
    description: '',
  })
  const [deleteConfirm, setDeleteConfirm] = useState<{ show: boolean; projectId: string; projectName: string } | null>(null)
  const [deleteTypedName, setDeleteTypedName] = useState('')
  const [apiKeyModal, setApiKeyModal] = useState<ApiKeyModalState>({ open: false })

  const portal = useMutation({
    mutationFn: api.billing.portal,
    onSuccess: (url) => {
      window.location.href = url
    },
    onError: (err: any) => {
      toast.error(err?.message || 'Unable to open billing portal')
    },
  })

  const copyToClipboard = async (
    value: string,
    messages: { success?: string; fallback?: string; label?: string } = {}
  ) => {
    try {
      await navigator.clipboard.writeText(value)
      if (messages.success) {
        toast.success(messages.success)
      }
    } catch {
      if (messages.fallback) {
        toast.success(messages.fallback)
      }
      toast(messages.label || 'Copied value', { description: value })
    }
  }

  const openApiKeyReveal = (apiKey: string, projectId: string, projectName: string, reason: ApiKeyRevealReason) => {
    setApiKeyModal({ open: true, mode: 'reveal', apiKey, projectId, projectName, reason })
  }

  const closeApiKeyModal = () => {
    if (rotateProjectKey.isPending && apiKeyModal.open && apiKeyModal.mode === 'confirm') {
      return
    }
    setApiKeyModal({ open: false })
  }

  const startRotateApiKey = (projectId: string, projectName: string) => {
    setApiKeyModal({ open: true, mode: 'confirm', projectId, projectName })
  }

  const confirmRotateApiKey = async () => {
    if (!apiKeyModal.open || apiKeyModal.mode !== 'confirm') {
      return
    }
    const { projectId, projectName } = apiKeyModal
    try {
      const result = await rotateProjectKey.mutateAsync(projectId)
      await copyToClipboard(result.ingest_api_key, {
        success: 'New API key copied to clipboard. Previous key is no longer valid.',
        fallback: 'New API key ready. Previous key is no longer valid.',
        label: 'API Key',
      })
      openApiKeyReveal(result.ingest_api_key, result.project_id, projectName, 'rotate')
    } catch (err: any) {
      toast.error(err?.message || 'Failed to rotate API key')
    }
  }

  const handleModalCopy = (apiKey: string) => {
    void copyToClipboard(apiKey, { success: 'API key copied to clipboard.', label: 'API Key' })
  }

  const handleCopyProjectId = (projectId: string) => {
    void copyToClipboard(projectId, { success: 'Project ID copied to clipboard.', label: 'Project ID' })
  }

  const handleCreateProject = async () => {
    if (data?.needs_subscription) {
      toast.error('Start a subscription to create projects.')
      return
    }
    try {
      const result = await createProject.mutateAsync(formState)
      setShowCreate(false)
      setFormState({ name: '', description: '' })
      await copyToClipboard(result.ingest_api_key, {
        success: 'Project created. API key copied to clipboard.',
        fallback: 'Project created. Copy the API key below.',
        label: 'API Key',
      })
      openApiKeyReveal(result.ingest_api_key, result.project.id, result.project.name, 'create')
    } catch (err: any) {
      toast.error(err?.message || 'Failed to create project')
    }
  }

  const handleDeleteProject = (projectId: string, projectName: string) => {
    setDeleteConfirm({ show: true, projectId, projectName })
    setDeleteTypedName('')
  }

  const confirmDeleteProject = () => {
    if (!deleteConfirm) return
    deleteProject.mutate(deleteConfirm.projectId, {
      onSuccess: () => {
        toast.success('Project deleted successfully')
        setDeleteConfirm(null)
        setDeleteTypedName('')
      },
      onError: (err: any) => {
        toast.error(err?.message || 'Failed to delete project')
      },
    })
  }

  if (isLoading) {
    return <div className="max-w-7xl mx-auto py-10 px-4">Loading projects...</div>
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto py-10 px-4 text-red-600">
        Failed to load projects: {String((error as any)?.message || 'Unknown error')}
      </div>
    )
  }

  const plan = data?.plan
  const needsSubscription = data?.needs_subscription ?? false
  const usage = data?.usage
  const projects = data?.projects ?? []
  const projectLimit = usage?.project_limit ?? null
  const projectPercent = projectLimit
    ? Math.min(100, Math.round((usage!.project_count / projectLimit) * 100))
    : 0

  return (
    <div className="min-h-screen bg-background dither-bg font-mono-jetbrains">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 space-y-8">
        <div className="flex items-center justify-between">
          <div className="space-y-4">
            <h1 className="text-4xl font-black dither-text leading-none">PROJECTS</h1>
            <div className="h-1 bg-foreground dither-border"></div>
            <p className="text-lg text-muted-foreground font-mono-jetbrains leading-relaxed">
              Manage retrieval workspaces, usage, and billing.
            </p>
          </div>
          <Dialog open={showCreate} onOpenChange={setShowCreate}>
            <DialogTrigger asChild>
              <Button
                disabled={needsSubscription}
                className={`${needsSubscription ? 'bg-red-500 border-red-500 hover:bg-red-600 hover:border-red-600' : 'bg-foreground text-background hover:bg-muted hover:text-foreground'} sharp-corners border-2 font-bold transition-all duration-200 dither-text px-6 py-3`}
              >
                {needsSubscription ? 'SUBSCRIPTION REQUIRED' : '[ CREATE PROJECT ]'}
              </Button>
            </DialogTrigger>
          <DialogContent className="bg-transparent border-none p-0 [&_[data-slot=dialog-close]]:top-6 [&_[data-slot=dialog-close]]:right-6">
            <div className="bg-card border-2 border-foreground dither-border sharp-corners p-6">
              <DialogHeader>
                <DialogTitle className="font-bold dither-text">NEW PROJECT</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 py-2">
                <div className="space-y-2">
                  <Label htmlFor="project-name" className="font-bold text-xs">// NAME</Label>
                  <Input
                    id="project-name"
                    placeholder="My App"
                    value={formState.name}
                    onChange={(event) => setFormState((prev) => ({ ...prev, name: event.target.value }))}
                    className="bg-background border border-foreground dither-border sharp-corners"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="project-description" className="font-bold text-xs">// DESCRIPTION (optional)</Label>
                  <Textarea
                    id="project-description"
                    rows={3}
                    value={formState.description ?? ''}
                    onChange={(event) =>
                      setFormState((prev) => ({ ...prev, description: event.target.value }))
                    }
                    className="bg-background border border-foreground dither-border sharp-corners"
                  />
                </div>
              </div>
              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => setShowCreate(false)}
                  className="bg-background border-2 border-foreground text-foreground sharp-corners font-bold hover:bg-foreground hover:text-background transition-all duration-200"
                >
                  [ CANCEL ]
                </Button>
                <Button
                  onClick={handleCreateProject}
                  disabled={!formState.name || createProject.isPending || data?.needs_subscription}
                  className="bg-foreground text-background border-2 border-foreground sharp-corners font-bold hover:bg-muted hover:text-foreground transition-all duration-200 dither-text"
                >
                  {createProject.isPending ? 'CREATING...' : '[ CREATE ]'}
                </Button>
              </DialogFooter>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {needsSubscription && (
        <Card className="bg-card border-2 border-foreground dither-border sharp-corners">
          <CardHeader className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div className="space-y-2">
              <CardTitle className="text-xl font-bold dither-text">NO ACTIVE SUBSCRIPTION</CardTitle>
              <CardDescription className="font-mono-jetbrains text-sm">
                Start a plan to unlock project creation, vector storage, and API access.
              </CardDescription>
            </div>
            <div className="flex gap-2">
              <Button
                asChild
                className="bg-foreground text-background border-2 border-foreground sharp-corners font-bold hover:bg-muted hover:text-foreground transition-all duration-200 dither-text px-4 py-2"
              >
                <Link to="/pricing">
                  [ GET SUBSCRIPTION ]
                </Link>
              </Button>
            </div>
          </CardHeader>
        </Card>
      )}

      {!needsSubscription && plan && usage && (
        <Card className="bg-card border-2 border-foreground dither-border sharp-corners">
          <CardHeader className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div className="space-y-2">
              <CardTitle className="text-xl font-bold dither-text">{plan.name.toUpperCase()} PLAN</CardTitle>
              <CardDescription className="font-mono-jetbrains text-sm">
                {plan.slug === 'tinkering'
                  ? 'Start on Tinkering and move to Building or Scale whenever you need more.'
                  : 'Your active subscription'}
              </CardDescription>
            </div>
            <div className="flex gap-2">
              {plan.slug !== 'scale' && (
                <Button
                  asChild
                  className="bg-foreground text-background border-2 border-foreground sharp-corners font-bold hover:bg-muted hover:text-foreground transition-all duration-200 dither-text px-4 py-2"
                >
                  <Link to="/pricing">
                    [ UPGRADE PLAN ]
                  </Link>
                </Button>
              )}
              {plan.slug !== 'tinkering' && (
                <Button
                  variant="ghost"
                  onClick={() => portal.mutate()}
                  disabled={portal.isPending}
                  className="bg-card border border-foreground dither-border sharp-corners font-bold hover:bg-muted transition-all duration-200"
                >
                  [ BILLING PORTAL ]
                </Button>
              )}
              </div>
          </CardHeader>
          <CardContent className="grid gap-6 md:grid-cols-3">
            <MetricCard title="QUERY QPS" value={`${plan.query_qps_limit}`} help="per second" />
            <MetricCard
              title="VECTORS PER PROJECT"
              value={
                plan?.vector_limit
                  ? formatNumber(plan.vector_limit)
                  : 'Unlimited'
              }
              help="Available per project"
            />
            <MetricCard title="PROJECTS" value={`${usage.project_count}`}>
              {projectLimit && (
                <Progress value={projectPercent} className="mt-2" />
              )}
            </MetricCard>
            <MetricCard title="TOTAL QUERIES" value={formatNumber(usage.total_queries)} />
            <MetricCard title="INGEST REQUESTS" value={formatNumber(usage.total_ingest_requests)} />
          </CardContent>
        </Card>
      )}

      <Card className="bg-card border-2 border-foreground dither-border sharp-corners">
        <CardHeader className="space-y-2">
          <CardTitle className="font-bold dither-text">PROJECTS</CardTitle>
          <CardDescription className="font-mono-jetbrains text-sm">
            Each project has its own vector store and API key.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {projects.length === 0 ? (
            <div className="text-sm text-muted-foreground font-mono-jetbrains bg-background border border-foreground dither-border sharp-corners p-4">
              <div className="text-xs font-bold mb-2">// SYSTEM STATUS</div>
              {needsSubscription
                ? 'Choose a subscription to start creating projects.'
                : 'No projects yet. Create one to get started.'}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="border-b border-foreground">
                  <TableHead className="font-bold text-xs">// NAME</TableHead>
                  <TableHead className="font-bold text-xs">// ID</TableHead>
                  <TableHead className="font-bold text-xs">// VECTORS</TableHead>
                  <TableHead className="font-bold text-xs text-right">// ACTIONS</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {projects.map((project) => (
                  <TableRow key={project.id} className="border-b border-foreground/20">
                    <TableCell className="font-medium">
                      <div className="flex flex-col space-y-1">
                        <span className="font-bold">{project.name}</span>
                        {project.description && (
                          <span className="text-xs text-muted-foreground font-mono-jetbrains">{project.description}</span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="font-mono-jetbrains">
                      <div className="flex items-center gap-2">
                        <span>{project.id}</span>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleCopyProjectId(project.id)}
                          className="bg-background border-2 border-foreground sharp-corners font-bold text-[10px] leading-none hover:bg-foreground hover:text-background transition-all duration-200"
                        >
                          [ COPY ]
                        </Button>
                      </div>
                    </TableCell>
                    <TableCell className="font-mono-jetbrains">{formatNumber(project.vector_count)}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          size="sm"
                          onClick={() => startRotateApiKey(project.id, project.name)}
                          disabled={rotateProjectKey.isPending && rotateProjectKey.variables === project.id}
                          className="bg-foreground text-background border-2 border-foreground sharp-corners font-bold hover:bg-muted hover:text-foreground transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {rotateProjectKey.isPending && rotateProjectKey.variables === project.id ? 'GENERATING...' : '[ NEW API KEY ]'}
                        </Button>
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => handleDeleteProject(project.id, project.name)}
                          disabled={deleteProject.isPending}
                          className="bg-red-600 text-white border-2 border-red-600 sharp-corners font-bold hover:bg-red-700 hover:border-red-700 transition-all duration-200"
                        >
                          [ DELETE ]
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteConfirm?.show ?? false} onOpenChange={(open) => !open && setDeleteConfirm(null)}>
        <DialogContent className="bg-transparent border-none p-0 [&_[data-slot=dialog-close]]:top-6 [&_[data-slot=dialog-close]]:right-6">
          <div className="bg-card border-2 border-red-600 dither-border sharp-corners p-6">
            <DialogHeader>
              <DialogTitle className="font-bold dither-text text-red-600">DELETE PROJECT</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <p className="text-sm font-mono-jetbrains">
                This action cannot be undone. This will permanently delete the project and all associated vectors.
              </p>
              <p className="text-sm font-mono-jetbrains font-bold">
                Please type <span className="bg-red-100 dark:bg-red-900/30 px-1">{deleteConfirm?.projectName}</span> to confirm:
              </p>
              <Input
                placeholder="Type project name here"
                value={deleteTypedName}
                onChange={(e) => setDeleteTypedName(e.target.value)}
                className="bg-background border-2 border-foreground dither-border sharp-corners font-mono-jetbrains"
                autoFocus
              />
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => {
                  setDeleteConfirm(null)
                  setDeleteTypedName('')
                }}
                className="bg-background border-2 border-foreground text-foreground sharp-corners font-bold hover:bg-foreground hover:text-background transition-all duration-200"
              >
                [ CANCEL ]
              </Button>
              <Button
                onClick={confirmDeleteProject}
                disabled={deleteTypedName !== deleteConfirm?.projectName || deleteProject.isPending}
                className="bg-red-600 text-white border-2 border-red-600 sharp-corners font-bold hover:bg-red-700 hover:border-red-700 transition-all duration-200 dither-text disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {deleteProject.isPending ? 'DELETING...' : '[ DELETE PROJECT ]'}
              </Button>
            </DialogFooter>
          </div>
        </DialogContent>
      </Dialog>

      <ApiKeyDialog
        state={apiKeyModal}
        onClose={closeApiKeyModal}
        onConfirmRotate={confirmRotateApiKey}
        onCopy={handleModalCopy}
        onCopyProjectId={handleCopyProjectId}
        isSubmitting={rotateProjectKey.isPending}
      />
      </div>
    </div>
  )
}

interface MetricCardProps {
  title: string
  value: string
  help?: string
  children?: ReactNode
}

function MetricCard({ title, value, help, children }: MetricCardProps) {
  return (
    <div className="bg-background border border-foreground dither-border sharp-corners p-4">
      <div className="text-xs font-bold text-muted-foreground mb-1">// {title}</div>
      <div className="text-2xl font-bold dither-text">{value}</div>
      {help && <div className="text-xs text-muted-foreground mt-1 font-mono-jetbrains">{help}</div>}
      {children}
    </div>
  )
}

interface ApiKeyDialogProps {
  state: ApiKeyModalState
  onClose: () => void
  onConfirmRotate: () => void
  onCopy: (apiKey: string) => void
  onCopyProjectId: (projectId: string) => void
  isSubmitting: boolean
}

function ApiKeyDialog({ state, onClose, onConfirmRotate, onCopy, onCopyProjectId, isSubmitting }: ApiKeyDialogProps) {
  const [copied, setCopied] = useState(false)
  const [idCopied, setIdCopied] = useState(false)

  const handleOpenChange = (open: boolean) => {
    if (!open) {
      if (state.open && state.mode === 'confirm' && isSubmitting) {
        return
      }
      setCopied(false)
      setIdCopied(false)
      onClose()
    }
  }

  const handleCopy = (apiKey: string) => {
    onCopy(apiKey)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleCopyProjectId = (projectId: string) => {
    onCopyProjectId(projectId)
    setIdCopied(true)
    setTimeout(() => setIdCopied(false), 2000)
  }

  const confirmState = state.open && state.mode === 'confirm' ? state : null
  const revealState = state.open && state.mode === 'reveal' ? state : null

  return (
    <Dialog open={state.open} onOpenChange={handleOpenChange}>
      {state.open && (
        <DialogContent className="bg-transparent border-none p-0 [&_[data-slot=dialog-close]]:top-6 [&_[data-slot=dialog-close]]:right-6">
          <div
            className={`bg-card border-2 ${confirmState ? 'border-amber-500' : 'border-foreground'} dither-border sharp-corners p-6`}
          >
            {confirmState && (
              <>
                <DialogHeader>
                  <DialogTitle className="font-bold dither-text text-amber-500">REPLACE PROJECT API KEY</DialogTitle>
                </DialogHeader>
                <div className="space-y-4 py-2 text-sm font-mono-jetbrains">
                  <p>
                    You're about to generate a new API key for <span className="font-bold">{confirmState.projectName}</span>.
                  </p>
                  <p className="text-red-600 font-bold">
                    The existing key will stop working immediately. Update any ingest clients before continuing.
                  </p>
                  <p className="text-xs text-muted-foreground">
                    This action cannot be undone. You'll receive the new key right after you confirm.
                  </p>
                </div>
                <DialogFooter>
                  <Button
                    variant="outline"
                    onClick={onClose}
                    disabled={isSubmitting}
                    className="bg-background border-2 border-foreground text-foreground sharp-corners font-bold hover:bg-foreground hover:text-background transition-all duration-200"
                  >
                    [ CANCEL ]
                  </Button>
                  <Button
                    onClick={onConfirmRotate}
                    disabled={isSubmitting}
                    className="bg-foreground text-background border-2 border-foreground sharp-corners font-bold hover:bg-muted hover:text-foreground transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isSubmitting ? 'GENERATING...' : '[ YES, REPLACE IT ]'}
                  </Button>
                </DialogFooter>
              </>
            )}

            {revealState && (
              <>
                <DialogHeader>
                  <DialogTitle className="font-bold dither-text">
                    {revealState.reason === 'create' ? 'PROJECT API KEY' : 'NEW API KEY ACTIVE'}
                  </DialogTitle>
                </DialogHeader>
                <div className="space-y-4 py-2">
                  <p className="text-sm font-mono-jetbrains">
                    {revealState.reason === 'create'
                      ? `This is the only time we will display the ingest API key for ${revealState.projectName}. Copy it and store it securely.`
                      : `The previous API key for ${revealState.projectName} has been revoked. Update your ingest clients with the key below immediately.`}
                  </p>
                  <div className="bg-background border-2 border-foreground dither-border sharp-corners flex items-center justify-between gap-3 px-4 py-3 font-mono-jetbrains text-sm break-all">
                    <span className="truncate">{revealState.apiKey}</span>
                    <Button
                      size="sm"
                      onClick={() => handleCopy(revealState.apiKey)}
                      className={`sharp-corners font-bold transition-all duration-200 ${
                        copied
                          ? 'bg-green-600 text-white border-green-600 hover:bg-green-600'
                          : 'bg-foreground text-background hover:bg-muted hover:text-foreground'
                      }`}
                    >
                      {copied ? '[ COPIED! ]' : '[ COPY ]'}
                    </Button>
                  </div>
                  <div className="bg-background border-2 border-foreground dither-border sharp-corners flex items-center justify-between gap-3 px-4 py-3 font-mono-jetbrains text-sm">
                    <span>Project ID: {revealState.projectId}</span>
                    <Button
                      size="sm"
                      onClick={() => handleCopyProjectId(revealState.projectId)}
                      className={`sharp-corners font-bold transition-all duration-200 ${
                        idCopied
                          ? 'bg-green-600 text-white border-green-600 hover:bg-green-600'
                          : 'bg-foreground text-background hover:bg-muted hover:text-foreground'
                      }`}
                    >
                      {idCopied ? '[ COPIED! ]' : '[ COPY ]'}
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground font-mono-jetbrains">
                    Safeguard this key. You can rotate it anytime from the Projects table if it is ever exposed.
                  </p>
                </div>
                <DialogFooter>
                  <Button
                    onClick={onClose}
                    className="bg-foreground text-background border-2 border-foreground sharp-corners font-bold hover:bg-muted hover:text-foreground"
                  >
                    [ CLOSE ]
                  </Button>
                </DialogFooter>
              </>
            )}
          </div>
        </DialogContent>
      )}
    </Dialog>
  )
}
