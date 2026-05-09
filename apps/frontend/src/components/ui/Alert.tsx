import clsx from 'clsx'
import type { ReactNode } from 'react'

type AlertVariant = 'info' | 'success' | 'warning' | 'error'

interface AlertProps {
  variant?: AlertVariant
  title?: string
  children: ReactNode
  className?: string
}

const styles: Record<AlertVariant, string> = {
  info: 'bg-blue-50 border-blue-200 text-blue-800',
  success: 'bg-green-50 border-green-200 text-green-800',
  warning: 'bg-amber-50 border-amber-200 text-amber-800',
  error: 'bg-red-50 border-red-200 text-red-800',
}

const icons: Record<AlertVariant, string> = {
  info: 'ℹ',
  success: '✓',
  warning: '⚠',
  error: '✕',
}

export default function Alert({ variant = 'info', title, children, className }: AlertProps) {
  return (
    <div className={clsx('rounded-xl border p-4', styles[variant], className)} role="alert">
      <div className="flex gap-3">
        <span className="shrink-0 font-bold">{icons[variant]}</span>
        <div className="text-sm">
          {title && <p className="mb-1 font-semibold">{title}</p>}
          <div>{children}</div>
        </div>
      </div>
    </div>
  )
}
