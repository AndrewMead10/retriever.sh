interface FAQItem {
  question: string
  answer: string
}

interface FAQSectionProps {
  title?: string
  subtitle?: string
  faqs?: FAQItem[]
  className?: string
}

export function FAQSection({
  title = 'FREQUENTLY ASKED QUESTIONS',
  subtitle = 'Everything you need to know about retriever.sh and our pricing.',
  faqs = DEFAULT_FAQS,
  className = '',
}: FAQSectionProps) {
  return (
    <div className={`${className}`}>
      <div className="text-center mb-12">
        <h2 className="text-4xl font-black dither-text mb-4">{title}</h2>
        <div className="h-1 bg-foreground w-24 mx-auto mb-6"></div>
        <p className="text-muted-foreground max-w-2xl mx-auto">{subtitle}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-6xl mx-auto">
        {faqs.map((faq, index) => (
          <div key={index} className="bg-card p-6 border border-foreground dither-border sharp-corners">
            <div className="flex items-start space-x-3">
              <span className="text-foreground font-bold text-lg">▶</span>
              <div>
                <h3 className="font-bold mb-2">{faq.question}</h3>
                <p className="text-sm text-muted-foreground">{faq.answer}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export const DEFAULT_FAQS: FAQItem[] = [
  {
    question: 'What makes retriever.sh different?',
    answer: 'Simple, affordable search with no infrastructure setup and easy integration with Claude Code.',
  },
  {
    question: 'How does Claude integration work?',
    answer: 'We have a Claude Skill file you can add to Claude Code so it automatically knows how to use our API.',
  },
  {
    question: 'How do I get started?',
    answer: 'Sign up, choose your plan, and get instant API access. No setup required - start building your search engine immediately.',
  },
  {
    question: 'Can I change plans anytime?',
    answer: 'Yes! Upgrade or downgrade anytime. Changes take effect at your next billing cycle.',
  },
]

export default FAQSection
