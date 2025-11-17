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
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { api, useCreateProject, useDeleteProject, useProjects } from '@/lib/api'
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

function ProjectsPage() {
  const { data, isLoading, error } = useProjects()
  const createProject = useCreateProject()
  const deleteProject = useDeleteProject()
  const [showCreate, setShowCreate] = useState(false)
  const [formState, setFormState] = useState<ProjectCreatePayload>({
    name: '',
    description: '',
  })
  const [deleteConfirm, setDeleteConfirm] = useState<{ show: boolean; projectId: number; projectName: string } | null>(null)
  const [deleteTypedName, setDeleteTypedName] = useState('')

  const portal = useMutation({
    mutationFn: api.billing.portal,
    onSuccess: (url) => {
      window.location.href = url
    },
    onError: (err: any) => {
      toast.error(err?.message || 'Unable to open billing portal')
    },
  })

  const handleCreateProject = async () => {
    if (data?.needs_subscription) {
      toast.error('Start a subscription to create projects.')
      return
    }
    try {
      const result = await createProject.mutateAsync(formState)
      setShowCreate(false)
      setFormState({ name: '', description: '' })
      toast.success('Project created. API key copied to clipboard.')
      try {
        await navigator.clipboard.writeText(result.ingest_api_key)
      } catch {
        toast('API Key', { description: result.ingest_api_key })
      }
    } catch (err: any) {
      toast.error(err?.message || 'Failed to create project')
    }
  }

  const handleDeleteProject = (projectId: number, projectName: string) => {
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
          <DialogContent className="bg-card border-2 border-foreground dither-border sharp-corners">
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
                        <Badge variant="outline" className="mt-1 w-fit bg-background border border-foreground dither-border sharp-corners">
                          ID #{project.id}
                        </Badge>
                      </div>
                    </TableCell>
                    <TableCell className="font-mono-jetbrains">{formatNumber(project.vector_count)}</TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => handleDeleteProject(project.id, project.name)}
                        disabled={deleteProject.isPending}
                        className="bg-red-600 text-white border-2 border-red-600 sharp-corners font-bold hover:bg-red-700 hover:border-red-700 transition-all duration-200"
                      >
                        [ DELETE ]
                      </Button>
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
        <DialogContent className="bg-card border-2 border-red-600 dither-border sharp-corners">
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
        </DialogContent>
      </Dialog>
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
