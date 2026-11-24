import { AlertCircle, Eye, HelpCircle, ShieldCheck, Wrench } from 'lucide-react';
import { uz } from '../i18n/uz';
import type { HealthPrediction } from '../types';

/**
 * What a diagnosis actually means.
 *
 * A name and a percentage are useless to someone standing in their garden.
 * The backend sends the whole library entry with every prediction, so this
 * shows what the disease is, how to recognise it, what to do today, and how
 * to avoid it next season.
 */

function Bullets({
  icon,
  title,
  items,
  tone = 'ink',
}: {
  icon: React.ReactNode;
  title: string;
  items: string[];
  tone?: 'ink' | 'action';
}) {
  if (!items.length) return null;
  const dot = tone === 'action' ? 'bg-tomato-500' : 'bg-leaf-500';
  return (
    <div>
      <h4 className="mb-1.5 flex items-center gap-2 text-base font-semibold text-ink-900 dark:text-white">
        <span className="text-leaf-600 dark:text-leaf-400" aria-hidden="true">
          {icon}
        </span>
        {title}
      </h4>
      <ul className="space-y-1.5">
        {items.map((item) => (
          <li
            key={item}
            className="flex gap-2.5 text-base leading-relaxed text-ink-600 dark:text-ink-300"
          >
            <span aria-hidden="true" className={`mt-2 h-1.5 w-1.5 shrink-0 rounded-full ${dot}`} />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function DiseaseGuide({ prediction }: { prediction: HealthPrediction }) {
  const signs = prediction.signs ?? [];
  const whatToDo = prediction.whatToDo ?? [];
  const prevent = prediction.prevent ?? [];

  // Older scans, saved before the library existed, carry no guidance.
  if (!prediction.whatIsIt && !signs.length && !whatToDo.length) return null;

  return (
    <div className="space-y-4 rounded-2xl bg-ink-50 p-4 dark:bg-night-900">
      {prediction.alsoCalled && (
        <p className="text-base text-ink-500 dark:text-ink-400">
          {uz.diseaseAlsoCalled}: {prediction.alsoCalled}
        </p>
      )}

      {prediction.whatIsIt && (
        <div>
          <h4 className="mb-1.5 flex items-center gap-2 text-base font-semibold text-ink-900 dark:text-white">
            <HelpCircle className="h-5 w-5 text-leaf-600 dark:text-leaf-400" aria-hidden="true" />
            {uz.diseaseWhatIsIt}
          </h4>
          <p className="text-base leading-relaxed text-ink-600 dark:text-ink-300">
            {prediction.whatIsIt}
          </p>
        </div>
      )}

      <Bullets icon={<Eye className="h-5 w-5" />} title={uz.diseaseSigns} items={signs} />

      {prediction.whyItHappens && (
        <div>
          <h4 className="mb-1.5 flex items-center gap-2 text-base font-semibold text-ink-900 dark:text-white">
            <AlertCircle className="h-5 w-5 text-leaf-600 dark:text-leaf-400" aria-hidden="true" />
            {uz.diseaseWhy}
          </h4>
          <p className="text-base leading-relaxed text-ink-600 dark:text-ink-300">
            {prediction.whyItHappens}
          </p>
        </div>
      )}

      <Bullets
        icon={<Wrench className="h-5 w-5" />}
        title={uz.diseaseWhatToDo}
        items={whatToDo}
        tone="action"
      />
      <Bullets
        icon={<ShieldCheck className="h-5 w-5" />}
        title={uz.diseasePrevent}
        items={prevent}
      />
    </div>
  );
}
