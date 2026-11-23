import { useState } from 'react';
import { CheckCircle2, Loader2, Server, XCircle } from 'lucide-react';
import { uz } from '../i18n/uz';
import { getBackendUrl, setBackendUrl } from '../lib/backend';
import { Button, Card, SectionTitle } from './ui';

type Status = 'idle' | 'checking' | 'ok' | 'bad';

/**
 * Lets the user point the app at a backend running elsewhere.
 *
 * Needed because the Netlify build is static: the API lives on the user's
 * own machine behind a tunnel whose URL changes whenever it restarts, and
 * storing it here avoids a redeploy every time.
 */
export function BackendSetting() {
  const [value, setValue] = useState(getBackendUrl());
  const [status, setStatus] = useState<Status>('idle');

  const save = async () => {
    setBackendUrl(value);
    setStatus('checking');
    try {
      const base = getBackendUrl();
      const response = await fetch(`${base}/api/health`, { credentials: 'include' });
      setStatus(response.ok ? 'ok' : 'bad');
    } catch {
      setStatus('bad');
    }
  };

  return (
    <Card className="space-y-3">
      <div className="flex items-center gap-2">
        <Server className="h-5 w-5 text-leaf-600 dark:text-leaf-400" aria-hidden="true" />
        <SectionTitle>{uz.backendTitle}</SectionTitle>
      </div>

      <p className="text-base leading-relaxed text-ink-600 dark:text-ink-300">
        {uz.backendHelp}
      </p>

      <label className="sr-only" htmlFor="backend-url">
        {uz.backendTitle}
      </label>
      <input
        id="backend-url"
        type="url"
        inputMode="url"
        autoComplete="off"
        spellCheck={false}
        value={value}
        placeholder={uz.backendPlaceholder}
        onChange={(event) => {
          setValue(event.target.value);
          setStatus('idle');
        }}
        className="min-h-[44px] w-full rounded-2xl border border-ink-200 bg-white px-3 text-base text-ink-900 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-leaf-500/40 dark:border-night-600 dark:bg-night-900 dark:text-white"
      />

      <Button block onClick={() => void save()} disabled={status === 'checking'}>
        {status === 'checking' ? (
          <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
        ) : (
          uz.backendSave
        )}
      </Button>

      {status === 'ok' && (
        <p className="flex items-center gap-2 text-base text-leaf-700 dark:text-leaf-300">
          <CheckCircle2 className="h-5 w-5 shrink-0" aria-hidden="true" />
          {uz.backendOk}
        </p>
      )}
      {status === 'bad' && (
        <p className="flex items-start gap-2 text-base text-tomato-700 dark:text-tomato-300">
          <XCircle className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
          {uz.backendBad}
        </p>
      )}
    </Card>
  );
}
