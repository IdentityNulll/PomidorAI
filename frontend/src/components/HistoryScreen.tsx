import { useCallback, useEffect, useState } from 'react';
import { Camera, ChevronRight, Loader2, Trash2 } from 'lucide-react';
import { uz } from '../i18n/uz';
import { deleteAllScans, deleteScan, getScans, scanThumbUrl } from '../lib/api';
import type { Scan } from '../types';
import { Button, Card } from './ui';
import { ConfirmDialog } from './ConfirmDialog';
import { ScanDetailSheet } from './ScanDetailSheet';
import { CONFIDENCE_FLOOR } from '../lib/confidence';

const PAGE_SIZE = 10;

type Pending = { kind: 'one'; id: string } | { kind: 'all' };

export function HistoryScreen({
  reloadKey,
  onStartScan,
}: {
  reloadKey: number;
  onStartScan: () => void;
}) {
  const [scans, setScans] = useState<Scan[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [openId, setOpenId] = useState<string | null>(null);
  const [pending, setPending] = useState<Pending | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const page = await getScans(null, PAGE_SIZE);
      setScans(page.scans);
      setCursor(page.cursor);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : uz.errorHistoryFailed);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load, reloadKey]);

  const loadMore = async () => {
    if (!cursor || loadingMore) return;
    setLoadingMore(true);
    try {
      const page = await getScans(cursor, PAGE_SIZE);
      setScans((current) => [...current, ...page.scans]);
      setCursor(page.cursor);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : uz.errorHistoryFailed);
    } finally {
      setLoadingMore(false);
    }
  };

  const confirmPending = async () => {
    if (!pending) return;
    const target = pending;
    setPending(null);
    try {
      if (target.kind === 'all') {
        await deleteAllScans();
        setScans([]);
        setCursor(null);
      } else {
        await deleteScan(target.id);
        setScans((current) => current.filter((scan) => scan.id !== target.id));
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : uz.errorDeleteFailed);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <Loader2 className="h-8 w-8 animate-spin text-leaf-600" aria-label={uz.loading} />
      </div>
    );
  }

  if (!scans.length) {
    return (
      <Card className="flex flex-col items-center gap-4 py-12 text-center">
        <span className="flex h-16 w-16 items-center justify-center rounded-2xl bg-leaf-100 dark:bg-leaf-500/15">
          <Camera className="h-8 w-8 text-leaf-600 dark:text-leaf-300" aria-hidden="true" />
        </span>
        <div>
          <h2 className="text-xl font-bold text-ink-900 dark:text-white">
            {uz.historyEmptyTitle}
          </h2>
          <p className="mt-1 text-base text-ink-500 dark:text-ink-400">
            {uz.historyEmptyMessage}
          </p>
        </div>
        <Button onClick={onStartScan} icon={<Camera className="h-5 w-5" />}>
          {uz.historyEmptyAction}
        </Button>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      {error && (
        <p className="rounded-2xl bg-tomato-50 p-4 text-base text-tomato-700 dark:bg-tomato-500/10 dark:text-tomato-300">
          {error}
        </p>
      )}

      <ul aria-label={uz.historyTitle} className="space-y-3">
        {scans.map((scan) => (
          <li key={scan.id}>
            <HistoryRow
              scan={scan}
              onOpen={() => setOpenId(scan.id)}
              onDelete={() => setPending({ kind: 'one', id: scan.id })}
            />
          </li>
        ))}
      </ul>

      {cursor && (
        <Button variant="secondary" block onClick={() => void loadMore()} disabled={loadingMore}>
          {loadingMore ? (
            <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
          ) : (
            uz.historyLoadMore
          )}
        </Button>
      )}

      <Button
        variant="ghost"
        block
        icon={<Trash2 className="h-5 w-5" />}
        onClick={() => setPending({ kind: 'all' })}
      >
        {uz.historyClearAll}
      </Button>

      {openId && <ScanDetailSheet scanId={openId} onClose={() => setOpenId(null)} />}

      {pending && (
        <ConfirmDialog
          title={pending.kind === 'all' ? uz.confirmClearTitle : uz.confirmDeleteTitle}
          message={pending.kind === 'all' ? uz.confirmClearMessage : uz.confirmDeleteMessage}
          confirmLabel={uz.confirmDelete}
          cancelLabel={uz.confirmCancel}
          onConfirm={() => void confirmPending()}
          onCancel={() => setPending(null)}
        />
      )}
    </div>
  );
}

function HistoryRow({
  scan,
  onOpen,
  onDelete,
}: {
  scan: Scan;
  onOpen: () => void;
  onDelete: () => void;
}) {
  const sure = scan.plant.confidence >= CONFIDENCE_FLOOR;
  const health = scan.health.predictions[0];

  return (
    <div className="flex items-center gap-3 rounded-3xl border border-ink-100 bg-white p-3 dark:border-night-700 dark:bg-night-800">
      <button
        onClick={onOpen}
        className="flex min-w-0 flex-1 items-center gap-3 rounded-2xl text-left focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-leaf-500/40"
      >
        {/* Fixed box + lazy loading: the row keeps its height before the image arrives. */}
        <span className="h-16 w-16 shrink-0 overflow-hidden rounded-2xl bg-ink-100 dark:bg-night-700">
          <img
            src={scanThumbUrl(scan.id)}
            alt={uz.historyThumbAlt}
            width={64}
            height={64}
            loading="lazy"
            className="h-full w-full object-cover"
          />
        </span>

        <span className="min-w-0 flex-1">
          <span className="block truncate text-base font-semibold text-ink-900 dark:text-white">
            {sure ? scan.plant.commonName || scan.plant.scientificName : uz.unknownPlant}
          </span>
          {health && (
            <span
              data-chrome
              className="mt-0.5 block truncate text-sm text-ink-600 dark:text-ink-300"
            >
              {health.label} · {Math.round(health.confidence * 100)}%
            </span>
          )}
          <span
            data-chrome
            className="mt-0.5 block text-sm text-ink-400 dark:text-ink-500"
          >
            {formatDate(scan.createdAt)}
          </span>
        </span>

        <ChevronRight
          className="h-5 w-5 shrink-0 text-ink-300 dark:text-ink-500"
          aria-hidden="true"
        />
      </button>

      <button
        onClick={onDelete}
        aria-label={uz.confirmDelete}
        className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl text-ink-400 transition-colors hover:bg-tomato-50 hover:text-tomato-600 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-tomato-500/40 dark:hover:bg-tomato-500/15 dark:hover:text-tomato-300"
      >
        <Trash2 className="h-5 w-5" aria-hidden="true" />
      </button>
    </div>
  );
}

function formatDate(value: string): string {
  // Backend timestamps are naive UTC, so mark them as UTC before formatting.
  const iso = value.endsWith('Z') || value.includes('+') ? value : `${value}Z`;
  return new Date(iso).toLocaleString('uz-UZ', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}
