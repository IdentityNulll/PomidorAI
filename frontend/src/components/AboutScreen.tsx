import { AlertTriangle, Camera, ShieldCheck, Sparkles, Leaf } from 'lucide-react';
import { uz } from '../i18n/uz';
import { Card, SectionTitle } from './ui';
import { Logo } from './Logo';
import { BackendSetting } from './BackendSetting';

export function AboutScreen() {
  const steps = [
    { icon: Camera, title: uz.aboutStep1Title, text: uz.aboutStep1Text },
    { icon: Sparkles, title: uz.aboutStep2Title, text: uz.aboutStep2Text },
    { icon: Leaf, title: uz.aboutStep3Title, text: uz.aboutStep3Text },
  ];

  return (
    <div className="space-y-4">
      <Card className="flex flex-col items-center gap-3 py-8 text-center">
        <Logo className="h-14 w-14" />
        <div>
          <h2 className="text-2xl font-bold text-ink-900 dark:text-white">{uz.appName}</h2>
          <p className="mt-1 text-base text-ink-500 dark:text-ink-400">{uz.appTagline}</p>
        </div>
      </Card>

      <Card className="space-y-5">
        <SectionTitle>{uz.aboutTitle}</SectionTitle>
        <ol className="space-y-5">
          {steps.map(({ icon: Icon, title, text }) => (
            <li key={title} className="flex gap-3.5">
              <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-leaf-100 text-leaf-700 dark:bg-leaf-500/15 dark:text-leaf-300">
                <Icon className="h-5 w-5" aria-hidden="true" />
              </span>
              <div className="min-w-0">
                <h3 className="text-base font-semibold text-ink-900 dark:text-white">{title}</h3>
                <p className="mt-0.5 text-base leading-relaxed text-ink-600 dark:text-ink-300">
                  {text}
                </p>
              </div>
            </li>
          ))}
        </ol>
      </Card>

      <Card className="space-y-2">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-5 w-5 text-leaf-600 dark:text-leaf-400" aria-hidden="true" />
          <h3 className="text-base font-semibold text-ink-900 dark:text-white">
            {uz.aboutPrivacyTitle}
          </h3>
        </div>
        <p className="text-base leading-relaxed text-ink-600 dark:text-ink-300">
          {uz.aboutPrivacyText}
        </p>
      </Card>

      <BackendSetting />

      <p className="flex gap-2.5 rounded-2xl bg-amber-50 p-4 text-base leading-relaxed text-amber-900 dark:bg-amber-500/10 dark:text-amber-200">
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
        <span>{uz.disclaimer}</span>
      </p>
    </div>
  );
}
