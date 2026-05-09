import Badge from '@/components/ui/Badge'

type BadgeVariantType = 'gray' | 'blue' | 'green' | 'amber' | 'red' | 'purple'

const INTENT_MAP: Record<string, { label: string; variant: BadgeVariantType }> = {
  policy_question: { label: 'Coverage Question', variant: 'blue' },
  jargon_definition: { label: 'Term Explained', variant: 'purple' },
  recommendation_followup: { label: 'Policy Follow-up', variant: 'green' },
  general_insurance: { label: 'Insurance Info', variant: 'gray' },
  greeting: { label: 'Greeting', variant: 'gray' },
  out_of_scope: { label: 'Out of Scope', variant: 'amber' },
  guardrailed: { label: 'Redirected', variant: 'amber' },
}

interface IntentBadgeProps {
  intent: string
}

export default function IntentBadge({ intent }: IntentBadgeProps) {
  const config = INTENT_MAP[intent] ?? { label: intent, variant: 'gray' as BadgeVariantType }
  return <Badge label={config.label} variant={config.variant} />
}
