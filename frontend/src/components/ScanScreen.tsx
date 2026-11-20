import { useEffect, useRef, useState } from 'react';
import { Camera, Images, Loader2, RotateCcw, Trash2, WifiOff } from 'lucide-react';
import { uz } from '../i18n/uz';
import { analyzeImage } from '../lib/api';
import { ImageError, prepareImage } from '../lib/image';
import type { ScanDetail } from '../types';
import { ResultView } from './ResultView';
import { Button, Card } from './ui';
import { Logo } from './Logo';

type Phase = 'idle' | 'ready' | 'analyzing' | 'done' | 'error';

export function ScanScreen({ online, onSaved }: { online: boolean; onSaved: () => void }) {
  const [phase, setPhase] = useState<Phase>('idle');
  const [preview, setPreview] = useState<string | null>(null);
  const [blob, setBlob] = useState<Blob | null>(null);
  const [scan, setScan] = useState<ScanDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cameraInput = useRef<HTMLInputElement>(null);
  const galleryInput = useRef<HTMLInputElement>(null);

  // The preview is an object URL, so it has to be released when it changes.
  useEffect(() => {
    if (!preview) return;
    return () => URL.revokeObjectURL(preview);
  }, [preview]);

  const reset = () => {
    setPhase('idle');
    setPreview(null);
    setBlob(null);
    setScan(null);
    setError(null);
  };

  const pick = async (file: File | undefined) => {
    if (!file) return;
    setError(null);
    try {
      const prepared = await prepareImage(file);
      setBlob(prepared);
      setPreview(URL.createObjectURL(prepared));
      setScan(null);
      setPhase('ready');
    } catch (cause) {
      setBlob(null);
      setPreview(null);
      setError(cause instanceof ImageError ? cause.message : uz.errorImageDecode);
      setPhase('error');
    }
  };

  const run = async (image: Blob) => {
    setPhase('analyzing');
    setError(null);
    try {
      const result = await analyzeImage(image);
      setScan(result);
      setPhase('done');
      onSaved();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : uz.errorAnalysisFailed);
      setPhase('error');
    }
  };

  if (phase === 'done' && scan) {
    return (
      <div className="space-y-4">
        <ResultView scan={scan} imageUrl={preview ?? undefined} />
        <Button variant="secondary" block icon={<Camera className="h-5 w-5" />} onClick={reset}>
          {uz.resultNewScan}
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <input
        ref={cameraInput}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={(event) => {
          void pick(event.target.files?.[0]);
          event.target.value = '';
        }}
      />
      <input
        ref={galleryInput}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(event) => {
          void pick(event.target.files?.[0]);
          event.target.value = '';
        }}
      />

      {preview ? (
        <div className="overflow-hidden rounded-3xl border border-ink-100 bg-ink-100 dark:border-night-700 dark:bg-night-800">
          <img
            src={preview}
            alt={uz.scanPreviewAlt}
            className="aspect-[4/3] w-full object-cover"
          />
        </div>
      ) : (
        <Card className="flex flex-col items-center gap-3 py-10 text-center">
          <Logo className="h-16 w-16" />
          <div>
            <h2 className="text-xl font-bold text-ink-900 dark:text-white">{uz.scanTitle}</h2>
            <p className="mt-1 text-base text-ink-500 dark:text-ink-400">{uz.scanSubtitle}</p>
          </div>
        </Card>
      )}

      {phase === 'analyzing' && (
        <Card className="flex items-center gap-3">
          <Loader2 className="h-6 w-6 shrink-0 animate-spin text-leaf-600" aria-hidden="true" />
          <div>
            <p className="text-base font-semibold text-ink-900 dark:text-white">{uz.analyzing}</p>
            <p className="text-base text-ink-500 dark:text-ink-400">{uz.analyzingHint}</p>
          </div>
        </Card>
      )}

      {error && phase !== 'analyzing' && (
        <Card className="space-y-3 border-tomato-200 bg-tomato-50 dark:border-tomato-500/30 dark:bg-tomato-500/10">
          <div>
            <p className="text-base font-semibold text-tomato-800 dark:text-tomato-200">
              {uz.errorTitle}
            </p>
            <p className="text-base text-tomato-700 dark:text-tomato-300">{error}</p>
          </div>
          {blob && (
            <Button
              variant="danger"
              block
              icon={<RotateCcw className="h-5 w-5" />}
              onClick={() => void run(blob)}
            >
              {uz.retry}
            </Button>
          )}
        </Card>
      )}

      {!online && (
        <Card className="flex gap-3 border-amber-200 bg-amber-50 dark:border-amber-500/30 dark:bg-amber-500/10">
          <WifiOff className="mt-0.5 h-5 w-5 shrink-0 text-amber-700 dark:text-amber-300" aria-hidden="true" />
          <div>
            <p className="text-base font-semibold text-amber-900 dark:text-amber-200">
              {uz.offlineTitle}
            </p>
            <p className="text-base leading-relaxed text-amber-800 dark:text-amber-300">
              {uz.offlineMessage}
            </p>
          </div>
        </Card>
      )}

      {phase === 'analyzing' ? null : blob ? (
        <div className="grid grid-cols-2 gap-3">
          <Button variant="secondary" icon={<Trash2 className="h-5 w-5" />} onClick={reset}>
            {uz.scanRemove}
          </Button>
          <Button
            icon={<Camera className="h-5 w-5" />}
            disabled={!online}
            onClick={() => void run(blob)}
          >
            {uz.scanAnalyze}
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          <Button
            block
            className="min-h-[64px] text-lg"
            icon={<Camera className="h-6 w-6" />}
            onClick={() => cameraInput.current?.click()}
          >
            {uz.scanCamera}
          </Button>
          <Button
            variant="secondary"
            block
            icon={<Images className="h-5 w-5" />}
            onClick={() => galleryInput.current?.click()}
          >
            {uz.scanGallery}
          </Button>
        </div>
      )}
    </div>
  );
}
