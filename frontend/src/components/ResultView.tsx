import { AlertTriangle, Droplets, Mountain, Sprout, Sun, CalendarDays } from 'lucide-react';
import { uz } from '../i18n/uz';
import type { ScanDetail } from '../types';
import { Card, ConfidenceBar, SectionTitle } from './ui';
import { CONFIDENCE_FLOOR } from '../lib/confidence';

/**
 * The species model knows 7806 plants but only a few hundred have an Uzbek
 * name, so commonName is often empty. Show the scientific name as the
 * heading rather than rendering a blank one.
 */
function displayName(plant: { commonName: string; scientificName: string }): string {
  return plant.commonName || plant.scientificName;
}

/** The backend reports what kind of photo it read: hosil, o'simlik or barg. */
const VIEW_LABELS: Record<string, string> = {
  hosil: uz.viewHosil,
  "o'simlik": uz.viewPlant,
  barg: uz.viewLeaf,
};

function ViewBadge({ view }: { view: string }) {
  const label = VIEW_LABELS[view];
  if (!label) return null;
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-leaf-100 px-2.5 py-1 text-base font-medium text-leaf-700 dark:bg-leaf-500/15 dark:text-leaf-300">
      {uz.viewLabel}: {label}
    </span>
  );
}

export function ResultView({ scan, imageUrl }: { scan: ScanDetail; imageUrl?: string }) {
  const plantSure = scan.plant.confidence >= CONFIDENCE_FLOOR;
  const predictions = scan.health.predictions;
  const healthSure = predictions.length > 0 && predictions[0].confidence >= CONFIDENCE_FLOOR;

  return (
    <div className="space-y-4">
      {imageUrl && (
        <div className="overflow-hidden rounded-3xl border border-ink-100 bg-ink-100 dark:border-night-700 dark:bg-night-800">
          <img
            src={imageUrl}
            alt={uz.scanPreviewAlt}
            className="aspect-[4/3] w-full object-cover"
          />
        </div>
      )}

      <Card className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <SectionTitle>{uz.resultPlantTitle}</SectionTitle>
          <ViewBadge view={scan.view ?? ""} />
        </div>
        {plantSure ? (
          <>
            <div>
              <h3 className="text-2xl font-bold leading-tight text-ink-900 dark:text-white">
                {displayName(scan.plant)}
              </h3>
              {scan.plant.commonName && (
                <p className="mt-0.5 text-base italic text-ink-500 dark:text-ink-400">
                  {scan.plant.scientificName}
                </p>
              )}
            </div>
            <ConfidenceBar label={uz.resultConfidence} value={scan.plant.confidence} emphasis />
          </>
        ) : (
          <Unsure />
        )}
      </Card>

      <Card className="space-y-4">
        <SectionTitle>{uz.resultHealthTitle}</SectionTitle>
        {healthSure ? (
          <div className="space-y-3.5">
            {predictions.slice(0, 3).map((prediction, index) => (
              <ConfidenceBar
                key={prediction.label}
                label={prediction.label}
                value={prediction.confidence}
                emphasis={index === 0}
              />
            ))}
          </div>
        ) : (
          <Unsure />
        )}
      </Card>

      {plantSure && <InfoCard info={scan.info} />}

      <p className="flex gap-2.5 rounded-2xl bg-amber-50 p-4 text-base leading-relaxed text-amber-900 dark:bg-amber-500/10 dark:text-amber-200">
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
        <span>{uz.disclaimer}</span>
      </p>
    </div>
  );
}

function Unsure() {
  return (
    <p className="rounded-2xl bg-ink-100 p-4 text-base leading-relaxed text-ink-700 dark:bg-night-700 dark:text-ink-200">
      {uz.resultUnsure}
    </p>
  );
}

function InfoCard({ info }: { info: ScanDetail['info'] }) {
  const facts = [
    { icon: Droplets, label: uz.resultWater, value: info.water },
    { icon: Sun, label: uz.resultSunlight, value: info.sunlight },
    { icon: Mountain, label: uz.resultSoil, value: info.soil },
    { icon: CalendarDays, label: uz.resultSeason, value: info.season },
    { icon: Sprout, label: uz.resultHowItGrows, value: info.howItGrows },
  ];

  return (
    <Card className="space-y-5">
      <SectionTitle>{uz.resultInfoTitle}</SectionTitle>

      <p className="text-base leading-relaxed text-ink-700 dark:text-ink-200">
        {info.description}
      </p>

      <dl className="space-y-4">
        {facts.map(({ icon: Icon, label, value }) => (
          <div key={label} className="flex gap-3">
            <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-leaf-100 text-leaf-700 dark:bg-leaf-500/15 dark:text-leaf-300">
              <Icon className="h-5 w-5" aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <dt className="text-base font-semibold text-ink-900 dark:text-white">{label}</dt>
              <dd className="text-base leading-relaxed text-ink-600 dark:text-ink-300">
                {value}
              </dd>
            </div>
          </div>
        ))}
      </dl>

      {info.commonDiseases.length > 0 && (
        <div>
          <h4 className="mb-2 text-base font-semibold text-ink-900 dark:text-white">
            {uz.resultCommonDiseases}
          </h4>
          <ul className="flex flex-wrap gap-2">
            {info.commonDiseases.map((disease) => (
              <li
                key={disease}
                className="rounded-full bg-tomato-50 px-3 py-1.5 text-base font-medium text-tomato-700 dark:bg-tomato-500/15 dark:text-tomato-200"
              >
                {disease}
              </li>
            ))}
          </ul>
        </div>
      )}

      {info.careTips.length > 0 && (
        <div>
          <h4 className="mb-2 text-base font-semibold text-ink-900 dark:text-white">
            {uz.resultCareTips}
          </h4>
          <ul className="space-y-2">
            {info.careTips.map((tip) => (
              <li
                key={tip}
                className="flex gap-2.5 text-base leading-relaxed text-ink-600 dark:text-ink-300"
              >
                <span aria-hidden="true" className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-leaf-500" />
                <span>{tip}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}
