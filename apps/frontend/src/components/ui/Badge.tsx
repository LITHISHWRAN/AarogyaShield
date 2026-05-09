import clsx from 'clsx'

type BadgeVariant = 'gray' | 'blue' | 'green' | 'amber' | 'red' | 'purple'

interface BadgeProps {
  label: string
  variant?: BadgeVariant
  className?: string
}

const variants: Record<BadgeVariant, string> = {
  gray: 'bg-gray-100 text-gray-600',
  blue: 'bg-blue-100 text-blue-700',
  green: 'bg-green-100 text-green-700',
  amber: 'bg-amber-100 text-amber-700',
  red: 'bg-red-100 text-red-700',
  purple: 'bg-purple-100 text-purple-700',
}

export default function Badge({ label, variant = 'gray', className }: BadgeProps) {
  return (
    <span
      className={clsx(
        'inline-block rounded-full px-2.5 py-0.5 text-xs font-medium',
        variants[variant],
        className,
      )}
    >
      {label}
    </span>
  )
}
