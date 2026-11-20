import { useEffect, useState } from 'react';
import { Loader2, X } from 'lucide-react';
import { uz } from '../i18n/uz';
import { getScan, scanImageUrl } from '../lib/api';
import type { ScanDetail } from '../types';
import { ResultView } from './ResultView';

export function ScanDetailSheet({
  scanId,
  onClose,
}: {
  scanId: string;
  onClose: () => void;
}) {
  const [scan, setScan] = useState<ScanDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getScan(scanId)
      .then((result) => active && setScan(result))
      .catch((cause: Error) => active && setError(cause.message));
    return () => {
      active = false;
    };
  }, [scanId]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => event.key === 'Escape' && onClose();
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [onClose]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={uz.historyTitle}
      className="fixed inset-0 z-50 flex flex-col bg-ink-50 dark:bg-night-900"
    >
      <header className="flex items-center justify-between gap-3 border-b border-ink-100 bg-white px-4 py-3 dark:border-night-700 dark:bg-night-800">
        <h2 className="truncate text-lg font-bold text-ink-900 dark:text-white">
          {scan ? scan.plant.commonName : uz.loading}
        </h2>
        <button
          onClick={onClose}
          aria-label={uz.close}
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl text-ink-500 transition-colors hover:bg-ink-100 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-leaf-500/40 dark:text-ink-300 dark:hover:bg-night-700"
        >
          <X className="h-5 w-5" aria-hidden="true" />
        </button>
      </header>

      <div
        className="flex-1 overflow-y-auto px-4 py-4"
        style={{ paddingBottom: 'calc(1rem + env(safe-area-inset-bottom))' }}
      >
        <div className="mx-auto w-full max-w-xl">
          {error && (
            <p className="rounded-2xl bg-tomato-50 p-4 text-base text-tomato-700 dark:bg-tomato-500/10 dark:text-tomato-300">
              {error}
            </p>
          )}
          {!scan && !error && (
            <div className="flex justify-center py-16">
              <Loader2 className="h-8 w-8 animate-spin text-leaf-600" aria-label={uz.loading} />
            </div>
          )}
          {scan && <ResultView scan={scan} imageUrl={scanImageUrl(scan.id)} />}
        </div>
      </div>
    </div>
  );
}
