import { expect, type Page } from '@playwright/test';

/** A tiny but valid JPEG, built in-process so no fixture file is needed. */
export async function makeJpeg(page: Page, size = 900): Promise<Buffer> {
  const dataUrl = await page.evaluate((side) => {
    const canvas = document.createElement('canvas');
    canvas.width = side;
    canvas.height = Math.round(side * 0.75);
    const context = canvas.getContext('2d')!;
    const gradient = context.createLinearGradient(0, 0, canvas.width, canvas.height);
    gradient.addColorStop(0, '#2e7d32');
    gradient.addColorStop(1, '#a5d6a7');
    context.fillStyle = gradient;
    context.fillRect(0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/jpeg', 0.9);
  }, size);

  return Buffer.from(dataUrl.split(',')[1], 'base64');
}

export async function uploadAndAnalyze(page: Page) {
  const buffer = await makeJpeg(page);
  await page
    .locator('input[type="file"]')
    .first()
    .setInputFiles({ name: 'leaf.jpg', mimeType: 'image/jpeg', buffer });

  await page.getByRole('button', { name: 'Tahlil qilish' }).click();
  await expect(page.getByRole('button', { name: 'Yangi tahlil' })).toBeVisible({
    timeout: 20_000,
  });
}

/** Fails if the document can scroll sideways. */
export async function expectNoHorizontalScroll(page: Page) {
  const overflow = await page.evaluate(() => {
    const doc = document.documentElement;
    return {
      scrollWidth: doc.scrollWidth,
      clientWidth: doc.clientWidth,
      widest: Array.from(document.querySelectorAll<HTMLElement>('body *'))
        .filter((el) => el.getBoundingClientRect().right > doc.clientWidth + 1)
        .slice(0, 5)
        .map((el) => `${el.tagName}.${el.className}`.slice(0, 120)),
    };
  });
  expect(
    overflow.scrollWidth,
    `page scrolls horizontally; offenders: ${overflow.widest.join(' | ')}`,
  ).toBeLessThanOrEqual(overflow.clientWidth);
}

/** Fails if any visible control is smaller than 44x44 CSS pixels. */
export async function expectTapTargets(page: Page) {
  const small = await page.evaluate(() => {
    const results: string[] = [];
    for (const el of document.querySelectorAll<HTMLElement>('button, a, input, select')) {
      if (el.offsetParent === null && el.tagName !== 'INPUT') continue;
      const style = getComputedStyle(el);
      if (style.display === 'none' || style.visibility === 'hidden') continue;
      const { width, height } = el.getBoundingClientRect();
      if (width === 0 && height === 0) continue; // hidden file inputs
      if (width < 44 || height < 44) {
        results.push(`${el.tagName} "${el.textContent?.trim().slice(0, 24)}" ${Math.round(width)}x${Math.round(height)}`);
      }
    }
    return results;
  });
  expect(small, `tap targets under 44px: ${small.join(' | ')}`).toEqual([]);
}

/**
 * Fails if content text renders below 16px.
 *
 * Elements marked `data-chrome` are exempt: nav labels, section eyebrows,
 * timestamps and percentages are UI furniture, not body copy, and 16px there
 * would crowd a 360px screen.
 */
export async function expectReadableText(page: Page) {
  const tiny = await page.evaluate(() => {
    const results: string[] = [];
    for (const el of document.querySelectorAll<HTMLElement>(
      'p, span, li, h1, h2, h3, h4, button, input, dd, dt',
    )) {
      if (el.closest('[data-chrome]')) continue;
      const text = Array.from(el.childNodes)
        .filter((node) => node.nodeType === Node.TEXT_NODE)
        .map((node) => node.textContent?.trim())
        .join('');
      if (!text) continue;
      if (el.getBoundingClientRect().height === 0) continue;
      const size = parseFloat(getComputedStyle(el).fontSize);
      if (size < 16) results.push(`${el.tagName} ${size}px "${text.slice(0, 32)}"`);
    }
    return results;
  });
  expect(tiny, `content text under 16px: ${tiny.join(' | ')}`).toEqual([]);
}
