import type { ButtonHTMLAttributes, ReactNode } from 'react';

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  icon?: ReactNode;
  block?: boolean;
};

const VARIANTS = {
  primary:
    'bg-leaf-600 text-white hover:bg-leaf-700 active:bg-leaf-800 shadow-sm shadow-leaf-600/25',
  secondary:
    'bg-white text-ink-700 border border-ink-200 hover:bg-ink-50 active:bg-ink-100 dark:bg-night-800 dark:text-ink-100 dark:border-night-600 dark:hover:bg-night-700',
  danger: 'bg-tomato-600 text-white hover:bg-tomato-700 active:bg-tomato-800',
  ghost:
    'text-ink-600 hover:bg-ink-100 active:bg-ink-200 dark:text-ink-300 dark:hover:bg-night-700',
} as const;

export function Button({
  variant = 'primary',
  icon,
  block,
  className = '',
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      className={[
        'inline-flex min-h-[48px] items-center justify-center gap-2 rounded-2xl px-5',
        'text-base font-semibold transition-all duration-150',
        'focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-leaf-500/40',
        'disabled:cursor-not-allowed disabled:opacity-50',
        'motion-safe:active:scale-[0.97]',
        block ? 'w-full' : '',
        VARIANTS[variant],
        className,
      ].join(' ')}
    >
      {icon}
      {children}
    </button>
  );
}

export function Card({
  children,
  className = '',
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={[
        'rounded-3xl border border-ink-100 bg-white p-5',
        'dark:border-night-700 dark:bg-night-800',
        className,
      ].join(' ')}
    >
      {children}
    </section>
  );
}

export function SectionTitle({ children }: { children: ReactNode }) {
  return (
    <h2
      data-chrome
      className="text-xs font-bold uppercase tracking-wider text-ink-500 dark:text-ink-400"
    >
      {children}
    </h2>
  );
}

export function ConfidenceBar({
  label,
  value,
  emphasis = false,
}: {
  label: string;
  value: number;
  emphasis?: boolean;
}) {
  const percent = Math.round(value * 100);
  const tone = emphasis ? 'bg-leaf-500' : 'bg-leaf-400/70 dark:bg-leaf-500/60';

  return (
    <div>
      <div className="mb-1.5 flex items-baseline justify-between gap-3">
        <span
          className={[
            'text-base',
            emphasis
              ? 'font-semibold text-ink-900 dark:text-white'
              : 'text-ink-700 dark:text-ink-200',
          ].join(' ')}
        >
          {label}
        </span>
        <span
          data-chrome
          className="shrink-0 text-sm font-semibold tabular-nums text-ink-500 dark:text-ink-400"
        >
          {percent}%
        </span>
      </div>
      <div
        className="h-2.5 overflow-hidden rounded-full bg-ink-100 dark:bg-night-700"
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label}
      >
        <div
          className={`h-full rounded-full transition-[width] duration-700 motion-reduce:transition-none ${tone}`}
          style={{ width: `${Math.max(percent, 2)}%` }}
        />
      </div>
    </div>
  );
}
