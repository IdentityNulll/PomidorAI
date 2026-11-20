import { Camera, History, Info } from 'lucide-react';
import { uz } from '../i18n/uz';
import type { Tab } from '../types-ui';

const TABS = [
  { id: 'scan', label: uz.tabScan, icon: Camera },
  { id: 'history', label: uz.tabHistory, icon: History },
  { id: 'about', label: uz.tabAbout, icon: Info },
] as const satisfies ReadonlyArray<{ id: Tab; label: string; icon: unknown }>;

/** Bottom tab bar on phones. Hidden at md and up, where TopNav takes over. */
export function BottomNav({
  active,
  onChange,
}: {
  active: Tab;
  onChange: (tab: Tab) => void;
}) {
  return (
    <nav
      data-chrome
      aria-label={uz.appName}
      className="sticky bottom-0 z-30 border-t border-ink-100 bg-white/95 backdrop-blur md:hidden dark:border-night-700 dark:bg-night-800/95"
      style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
    >
      <ul className="flex">
        {TABS.map(({ id, label, icon: Icon }) => {
          const selected = active === id;
          return (
            <li key={id} className="flex-1">
              <button
                onClick={() => onChange(id)}
                aria-current={selected ? 'page' : undefined}
                className={[
                  'flex min-h-[56px] w-full flex-col items-center justify-center gap-1 px-1 py-2',
                  'text-xs font-semibold transition-colors',
                  'focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-inset focus-visible:ring-leaf-500/40',
                  'motion-safe:active:scale-95',
                  selected
                    ? 'text-leaf-700 dark:text-leaf-300'
                    : 'text-ink-500 dark:text-ink-400',
                ].join(' ')}
              >
                <Icon className="h-6 w-6" aria-hidden="true" />
                {label}
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

/** Horizontal nav shown in the header on wide screens. */
export function TopNav({
  active,
  onChange,
}: {
  active: Tab;
  onChange: (tab: Tab) => void;
}) {
  return (
    <nav data-chrome aria-label={uz.appName} className="hidden md:block">
      <ul className="flex gap-1">
        {TABS.map(({ id, label, icon: Icon }) => {
          const selected = active === id;
          return (
            <li key={id}>
              <button
                onClick={() => onChange(id)}
                aria-current={selected ? 'page' : undefined}
                className={[
                  'flex min-h-[44px] items-center gap-2 rounded-2xl px-4 text-base font-semibold',
                  'transition-colors focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-leaf-500/40',
                  selected
                    ? 'bg-leaf-100 text-leaf-800 dark:bg-leaf-500/15 dark:text-leaf-200'
                    : 'text-ink-600 hover:bg-ink-100 dark:text-ink-300 dark:hover:bg-night-700',
                ].join(' ')}
              >
                <Icon className="h-5 w-5" aria-hidden="true" />
                {label}
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
