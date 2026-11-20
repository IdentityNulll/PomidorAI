import { useState } from 'react';
import { WifiOff } from 'lucide-react';
import { uz } from './i18n/uz';
import { useOnline } from './hooks/useOnline';
import { AboutScreen } from './components/AboutScreen';
import { HistoryScreen } from './components/HistoryScreen';
import { ScanScreen } from './components/ScanScreen';
import { BottomNav, TopNav } from './components/Navigation';
import { Logo } from './components/Logo';
import type { Tab } from './types-ui';

export default function App() {
  const [tab, setTab] = useState<Tab>('scan');
  const [historyKey, setHistoryKey] = useState(0);
  const online = useOnline();

  return (
    <div className="flex min-h-[100dvh] flex-col bg-ink-50 dark:bg-night-900">
      <header className="sticky top-0 z-30 border-b border-ink-100 bg-white/95 backdrop-blur dark:border-night-700 dark:bg-night-800/95">
        <div className="mx-auto flex w-full max-w-3xl items-center justify-between gap-3 px-4 py-3">
          <div className="flex min-w-0 items-center gap-2.5">
            <Logo className="h-8 w-8 shrink-0" />
            <span className="truncate text-lg font-bold tracking-tight text-ink-900 dark:text-white">
              {uz.appName}
            </span>
          </div>
          <TopNav active={tab} onChange={setTab} />
        </div>
      </header>

      {!online && (
        <p
          data-chrome
          role="status"
          className="flex items-center justify-center gap-2 bg-amber-100 px-4 py-2.5 text-center text-sm font-medium text-amber-900 dark:bg-amber-500/15 dark:text-amber-200"
        >
          <WifiOff className="h-4 w-4 shrink-0" aria-hidden="true" />
          {uz.offlineBanner}
        </p>
      )}

      <main className="flex-1 px-4 py-4">
        <div className="mx-auto w-full max-w-3xl">
          {tab === 'scan' && (
            <ScanScreen online={online} onSaved={() => setHistoryKey((key) => key + 1)} />
          )}
          {tab === 'history' && (
            <HistoryScreen reloadKey={historyKey} onStartScan={() => setTab('scan')} />
          )}
          {tab === 'about' && <AboutScreen />}
        </div>
      </main>

      <BottomNav active={tab} onChange={setTab} />
    </div>
  );
}
