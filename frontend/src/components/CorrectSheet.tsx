import { useEffect, useState } from 'react';
import { Check, Loader2 } from 'lucide-react';
import { uz } from '../i18n/uz';
import { correctScan, getPlants } from '../lib/api';
import type { PlantOption, ScanDetail } from '../types';
import { Button } from './ui';

/**
 * Lets the user say what a plant actually was.
 *
 * The correction is stored with the photo's CLIP embedding, so a similar
 * photo is recognised next time - no retraining run involved.
 */
export function CorrectSheet({
  scanId,
  onSaved,
  onCancel,
}: {
  scanId: string;
  onSaved: (scan: ScanDetail) => void;
  onCancel: () => void;
}) {
  const [plants, setPlants] = useState<PlantOption[]>([]);
  const [saving, setSaving] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getPlants()
      .then(setPlants)
      .catch(() => setError(uz.errorCorrectFailed));
  }, []);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => event.key === 'Escape' && onCancel();
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onCancel]);

  const choose = async (plantId: string) => {
    setSaving(plantId);
    setError(null);
    try {
      onSaved(await correctScan(scanId, plantId));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : uz.errorCorrectFailed);
      setSaving(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center">
      <div className="absolute inset-0 bg-ink-900/50" onClick={onCancel} />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="correct-title"
        className="relative flex max-h-[85dvh] w-full max-w-sm flex-col rounded-t-3xl bg-white p-5 pb-[max(1.25rem,env(safe-area-inset-bottom))] shadow-xl dark:bg-night-800 sm:rounded-3xl"
      >
        <h2 id="correct-title" className="text-lg font-bold text-ink-900 dark:text-white">
          {uz.correctTitle}
        </h2>

        {error && (
          <p className="mt-2 rounded-2xl bg-tomato-50 p-3 text-base text-tomato-700 dark:bg-tomato-500/10 dark:text-tomato-300">
            {error}
          </p>
        )}

        <ul className="-mx-1 mt-3 flex-1 overflow-y-auto overscroll-contain px-1">
          {plants.map((plant) => (
            <li key={plant.id}>
              <button
                onClick={() => void choose(plant.id)}
                disabled={saving !== null}
                className="flex min-h-[44px] w-full items-center justify-between gap-3 rounded-2xl px-3 py-2.5 text-left hover:bg-leaf-50 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-leaf-500/40 disabled:opacity-50 dark:hover:bg-night-700"
              >
                <span className="min-w-0">
                  <span className="block truncate text-base font-semibold text-ink-900 dark:text-white">
                    {plant.commonName}
                  </span>
                  <span className="block truncate text-base italic text-ink-500 dark:text-ink-400">
                    {plant.scientificName}
                  </span>
                </span>
                {saving === plant.id ? (
                  <Loader2 className="h-5 w-5 shrink-0 animate-spin text-leaf-600" />
                ) : (
                  <Check className="h-5 w-5 shrink-0 text-ink-300 dark:text-ink-500" />
                )}
              </button>
            </li>
          ))}
        </ul>

        <Button variant="secondary" block onClick={onCancel} className="mt-3">
          {uz.correctCancel}
        </Button>
      </div>
    </div>
  );
}
