import { createFileRoute } from '@tanstack/react-router'
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Mail, MessageCircle, Send, ExternalLink } from 'lucide-react'

interface ConnectFormData {
  name: string
  email: string
  subject: string
  message: string
}

interface ConnectPageData {
  discord_link: string
  support_email: string
  contact_info: {
    email: string
    response_time: string
  }
}

export const Route = createFileRoute('/connect/')({
  loader: async () => {
    try {
      const response = await fetch('/api/connect/onload')
      if (!response.ok) {
        throw new Error('Failed to load connect page data')
      }
      return await response.json() as ConnectPageData
    } catch (error) {
      console.error('Failed to load connect page data:', error)
      // Return fallback data
      return {
        discord_link: "https://discord.gg/YOUR_DISCORD_INVITE",
        support_email: "support@retriever.sh",
        contact_info: {
          email: "support@retriever.sh",
          response_time: "24-48 hours"
        }
      }
    }
  },
  component: ConnectPage,
})

function ConnectPage() {
  const data = Route.useLoaderData()
  const [formData, setFormData] = useState<ConnectFormData>({
    name: '',
    email: '',
    subject: '',
    message: ''
  })

  const submitMutation = useMutation({
    mutationFn: async (data: ConnectFormData) => {
      const response = await fetch('/api/connect/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      })

      if (!response.ok) {
        const error = await response.json().catch(() => ({}))
        throw new Error(error.detail || error.message || 'Failed to submit contact form')
      }

      return response.json()
    },
    onSuccess: (result) => {
      toast.success(result.message)
      setFormData({ name: '', email: '', subject: '', message: '' })
    },
    onError: (error: Error) => {
      toast.error(error.message)
    },
  })

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!formData.name || !formData.email || !formData.subject || !formData.message) {
      toast.error('Please fill in all fields')
      return
    }

    submitMutation.mutate(formData)
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="text-center mb-12">
            <h1 className="text-4xl font-black font-mono-jetbrains mb-4 dither-text">
              GET IN TOUCH
            </h1>
            <p className="text-lg text-muted-foreground font-mono-jetbrains">
              We're here to help and answer any questions you might have
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-8">
            {/* Contact Form */}
            <Card className="dither-border sharp-corners border-2">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 font-mono-jetbrains">
                  <Mail className="h-5 w-5" />
                  SEND US A MESSAGE
                </CardTitle>
                <CardDescription className="font-mono-jetbrains">
                  Fill out the form below and we'll get back to you within {data.contact_info.response_time}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="name" className="font-mono-jetbrains text-sm">NAME</Label>
                      <Input
                        id="name"
                        name="name"
                        type="text"
                        value={formData.name}
                        onChange={handleInputChange}
                        className="sharp-corners font-mono-jetbrains"
                        placeholder="Your name"
                      />
                    </div>
                    <div>
                      <Label htmlFor="email" className="font-mono-jetbrains text-sm">EMAIL</Label>
                      <Input
                        id="email"
                        name="email"
                        type="email"
                        value={formData.email}
                        onChange={handleInputChange}
                        className="sharp-corners font-mono-jetbrains"
                        placeholder="your@email.com"
                      />
                    </div>
                  </div>

                  <div>
                    <Label htmlFor="subject" className="font-mono-jetbrains text-sm">SUBJECT</Label>
                    <Input
                      id="subject"
                      name="subject"
                      type="text"
                      value={formData.subject}
                      onChange={handleInputChange}
                      className="sharp-corners font-mono-jetbrains"
                      placeholder="What's this about?"
                    />
                  </div>

                  <div>
                    <Label htmlFor="message" className="font-mono-jetbrains text-sm">MESSAGE</Label>
                    <Textarea
                      id="message"
                      name="message"
                      value={formData.message}
                      onChange={handleInputChange}
                      className="sharp-corners font-mono-jetbrains min-h-[120px]"
                      placeholder="Tell us what's on your mind..."
                    />
                  </div>

                  <Button
                    type="submit"
                    disabled={submitMutation.isPending}
                    className="w-full sharp-corners font-mono-jetbrains font-bold bg-foreground hover:bg-muted text-background"
                  >
                    <div className="flex items-center gap-2">
                      <Send className="h-4 w-4" />
                      {submitMutation.isPending ? 'SENDING...' : 'SEND MESSAGE'}
                    </div>
                  </Button>
                </form>
              </CardContent>
            </Card>

            {/* Quick Contact Options */}
            <div className="space-y-6">
              {/* Discord Card */}
              <Card className="dither-border sharp-corners border-2">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 font-mono-jetbrains">
                    <MessageCircle className="h-5 w-5" />
                    JOIN OUR DISCORD
                  </CardTitle>
                  <CardDescription className="font-mono-jetbrains">
                    Get instant help and connect with our community
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <p className="text-sm text-muted-foreground font-mono-jetbrains">
                      Join our Discord server for real-time support, feature requests, and to connect with other users.
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <Badge variant="secondary" className="font-mono-jetbrains">LIVE SUPPORT</Badge>
                      <Badge variant="secondary" className="font-mono-jetbrains">COMMUNITY</Badge>
                      <Badge variant="secondary" className="font-mono-jetbrains">UPDATES</Badge>
                    </div>
                    <Button
                      asChild
                      className="w-full sharp-corners font-mono-jetbrains font-bold bg-indigo-600 hover:bg-indigo-700"
                    >
                      <a
                        href={data.discord_link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center justify-center gap-2"
                      >
                        <ExternalLink className="h-4 w-4" />
                        JOIN DISCORD
                      </a>
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* Email Support Card */}
              <Card className="dither-border sharp-corners border-2">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 font-mono-jetbrains">
                    <Mail className="h-5 w-5" />
                    EMAIL SUPPORT
                  </CardTitle>
                  <CardDescription className="font-mono-jetbrains">
                    Direct email support for technical issues
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <p className="text-sm text-muted-foreground font-mono-jetbrains">
                      For technical support, billing questions, or other inquiries, email us directly.
                    </p>
                    <div className="bg-muted p-3 rounded sharp-corners">
                      <p className="font-mono-jetbrains font-bold text-center">
                        {data.support_email}
                      </p>
                    </div>
                    <div className="text-center">
                      <p className="text-xs text-muted-foreground font-mono-jetbrains">
                        Response time: {data.contact_info.response_time}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Resources */}
              <Card className="dither-border sharp-corners border-2">
                <CardHeader>
                  <CardTitle className="font-mono-jetbrains">OTHER RESOURCES</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <Button
                      variant="ghost"
                      asChild
                      className="w-full justify-start font-mono-jetbrains sharp-corners"
                    >
                      <a href="/documentation">DOCUMENTATION</a>
                    </Button>
                    <Button
                      variant="ghost"
                      asChild
                      className="w-full justify-start font-mono-jetbrains sharp-corners"
                    >
                      <a href="/#pricing">PRICING</a>
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}