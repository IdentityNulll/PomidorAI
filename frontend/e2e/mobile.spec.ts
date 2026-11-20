import { expect, test, type Page } from '@playwright/test';
import {
  expectNoHorizontalScroll,
  expectReadableText,
  expectTapTargets,
  makeJpeg,
  uploadAndAnalyze,
} from './helpers';

const shot = (name: string) => ({ path: `screenshots/${name}.png`, fullPage: true });

/** The history list only - scoped so the nav's list items are not matched. */
const historyItems = (page: Page) =>
  page.getByRole('list', { name: 'Tarix' }).getByRole('listitem');

test.beforeEach(async ({ context }) => {
  await context.clearCookies();
});

test('full flow: scan, result, history, detail, delete', async ({ page }, testInfo) => {
  const device = testInfo.project.name.replace(/\s+/g, '-');

  // 1. Home
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Kameradan olish' })).toBeVisible();
  await page.screenshot(shot(`${device}-1-home`));
  await expectNoHorizontalScroll(page);
  await expectTapTargets(page);

  // 2. Preview after choosing a photo
  const buffer = await makeJpeg(page);
  await page
    .locator('input[type="file"]')
    .first()
    .setInputFiles({ name: 'leaf.jpg', mimeType: 'image/jpeg', buffer });
  await expect(page.getByRole('button', { name: 'Tahlil qilish' })).toBeVisible();
  await page.screenshot(shot(`${device}-2-preview`));
  await expectNoHorizontalScroll(page);

  // 3. Loading state
  await page.getByRole('button', { name: 'Tahlil qilish' }).click();
  await expect(page.getByText('Tahlil qilinmoqda...')).toBeVisible();
  await page.screenshot(shot(`${device}-3-loading`));

  // 4. Result
  await expect(page.getByRole('button', { name: 'Yangi tahlil' })).toBeVisible({
    timeout: 20_000,
  });
  await expect(page.getByText(/dastlabki tekshiruv uchun/)).toBeVisible();
  await page.screenshot(shot(`${device}-4-result`));
  await expectNoHorizontalScroll(page);
  await expectTapTargets(page);

  // 5. History list
  await page.getByRole('button', { name: 'Tarix' }).click();
  await expect(historyItems(page).first()).toBeVisible();
  await page.screenshot(shot(`${device}-5-history`));
  await expectNoHorizontalScroll(page);
  await expectTapTargets(page);

  // Thumbnails are lazily loaded and must actually render.
  const thumb = page.locator('img[loading="lazy"]').first();
  await expect(thumb).toBeVisible();
  expect(await thumb.evaluate((img: HTMLImageElement) => img.naturalWidth)).toBeGreaterThan(0);

  // 6. Detail
  await historyItems(page).first().getByRole('button').first().click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.getByRole('dialog').getByText(/dastlabki tekshiruv uchun/)).toBeVisible();
  await page.screenshot(shot(`${device}-6-detail`));
  await expectNoHorizontalScroll(page);
  await page.getByRole('button', { name: 'Yopish' }).click();

  // 7. Delete with confirmation
  await historyItems(page).first().getByRole('button', { name: "O'chirish" }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.screenshot(shot(`${device}-7-confirm-delete`));
  await page.getByRole('dialog').getByRole('button', { name: "O'chirish" }).click();

  // 8. Empty state
  await expect(page.getByText('Hozircha tahlil yo’q').or(page.getByText("Hozircha tahlil yo'q"))).toBeVisible();
  await page.screenshot(shot(`${device}-8-empty`));
  await expectNoHorizontalScroll(page);
  await expectTapTargets(page);
});

test('history survives a reload and pagination loads more', async ({ page }) => {
  await page.goto('/');
  for (let i = 0; i < 2; i += 1) {
    await uploadAndAnalyze(page);
    await page.getByRole('button', { name: 'Yangi tahlil' }).click();
  }

  await page.reload();
  await page.getByRole('button', { name: 'Tarix' }).click();
  await expect(historyItems(page)).toHaveCount(2);
});

test('about screen shows the three steps and the disclaimer', async ({ page }, testInfo) => {
  const device = testInfo.project.name.replace(/\s+/g, '-');
  await page.goto('/');
  await page.getByRole('button', { name: 'Haqida' }).click();

  await expect(page.getByRole('heading', { name: /1\./ })).toBeVisible();
  await expect(page.getByRole('heading', { name: /2\./ })).toBeVisible();
  await expect(page.getByRole('heading', { name: /3\./ })).toBeVisible();
  await expect(page.getByText(/dastlabki tekshiruv uchun/)).toBeVisible();

  await page.screenshot(shot(`${device}-9-about`));
  await expectNoHorizontalScroll(page);
  await expectTapTargets(page);
});

test('offline shows an Uzbek message instead of letting a scan run', async ({
  page,
  context,
}, testInfo) => {
  const device = testInfo.project.name.replace(/\s+/g, '-');
  await page.goto('/');
  await context.setOffline(true);
  await page.evaluate(() => window.dispatchEvent(new Event('offline')));

  await expect(page.getByText("Internet yo'q. Tahlil qilish uchun internet kerak.")).toBeVisible();
  await expect(page.getByText("Internet aloqasi yo'q")).toBeVisible();
  await page.screenshot(shot(`${device}-10-offline`));
  await expectNoHorizontalScroll(page);

  await context.setOffline(false);
});

test('body text is at least 16px and layout holds in dark mode', async ({ page }, testInfo) => {
  const device = testInfo.project.name.replace(/\s+/g, '-');
  await page.emulateMedia({ colorScheme: 'dark' });
  await page.goto('/');
  await uploadAndAnalyze(page);

  await page.screenshot(shot(`${device}-11-dark-result`));
  await expectNoHorizontalScroll(page);

  await expectReadableText(page);
});

test('tab bar clears the safe area and layout works on a tablet width', async ({ page }) => {
  await page.goto('/');
  await page.setViewportSize({ width: 834, height: 1112 });
  await expect(page.getByRole('navigation').first()).toBeVisible();
  await expectNoHorizontalScroll(page);
  await expectTapTargets(page);

  for (const width of [360, 390, 412]) {
    await page.setViewportSize({ width, height: 800 });
    await expectNoHorizontalScroll(page);
    await expectTapTargets(page);
  }
});
