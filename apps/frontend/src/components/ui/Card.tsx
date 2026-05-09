import clsx from 'clsx'
import type { ReactNode } from 'react'

interface CardProps {
  children: ReactNode
  className?: string
  padding?: 'sm' | 'md' | 'lg'
}

export default function Card({ children, className, padding = 'md' }: CardProps) {
  return (
    <div
      className={clsx(
        'rounded-2xl bg-white shadow-sm ring-1 ring-gray-100',
        { 'p-4': padding === 'sm', 'p-6': padding === 'md', 'p-8': padding === 'lg' },
        className,
      )}
    >
      {children}
    </div>
  )
}
