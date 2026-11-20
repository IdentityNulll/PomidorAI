import { expect, test } from '@playwright/test';
import { expectNoHorizontalScroll, makeJpeg } from './helpers';

const shot = (name: string) => ({ path: `screenshots/${name}.png`, fullPage: true });

async function choosePhoto(page: import('@playwright/test').Page) {
  const buffer = await makeJpeg(page);
  await page
    .locator('input[type="file"]')
    .first()
    .setInputFiles({ name: 'leaf.jpg', mimeType: 'image/jpeg', buffer });
  await expect(page.getByRole('button', { name: 'Tahlil qilish' })).toBeVisible();
}

test('low confidence hides the name and asks for a clearer photo', async ({
  page,
}, testInfo) => {
  const device = testInfo.project.name.replace(/\s+/g, '-');

  await page.route('**/api/analyze', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'low-confidence',
        createdAt: new Date().toISOString(),
        plant: {
          id: 'tomato',
          commonName: 'Pomidor',
          scientificName: 'Solanum lycopersicum',
          confidence: 0.31,
        },
        health: { predictions: [{ label: "Sog'lom", confidence: 0.34 }] },
        info: {
          description: 'x',
          howItGrows: 'x',
          water: 'x',
          sunlight: 'x',
          soil: 'x',
          season: 'x',
          commonDiseases: [],
          careTips: [],
        },
      }),
    }),
  );

  await page.goto('/');
  await choosePhoto(page);
  await page.getByRole('button', { name: 'Tahlil qilish' }).click();

  const unsure = page.getByText(
    "Ishonchim komil emas. Bitta barg yoki o'simlikning aniqroq rasmini yuboring.",
  );
  // Shown for both the plant and the health section.
  await expect(unsure).toHaveCount(2);

  // The name must not leak through when the model is unsure.
  await expect(page.getByText('Pomidor', { exact: true })).toHaveCount(0);
  await expect(page.getByText('Solanum lycopersicum')).toHaveCount(0);

  await page.screenshot(shot(`${device}-12-low-confidence`));
  await expectNoHorizontalScroll(page);
});

test('a failed analysis shows an error with a working retry', async ({ page }, testInfo) => {
  const device = testInfo.project.name.replace(/\s+/g, '-');

  let attempts = 0;
  await page.route('**/api/analyze', (route) => {
    attempts += 1;
    if (attempts === 1) {
      return route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: "Tahlil qilib bo'lmadi" }),
      });
    }
    return route.fallback();
  });

  await page.goto('/');
  await choosePhoto(page);
  await page.getByRole('button', { name: 'Tahlil qilish' }).click();

  await expect(page.getByText('Xatolik yuz berdi')).toBeVisible();
  const retry = page.getByRole('button', { name: 'Qayta urinish' });
  await expect(retry).toBeVisible();
  await page.screenshot(shot(`${device}-13-error`));
  await expectNoHorizontalScroll(page);

  // Retrying hits the real endpoint and succeeds.
  await retry.click();
  await expect(page.getByRole('button', { name: 'Yangi tahlil' })).toBeVisible({
    timeout: 20_000,
  });
});

test('an undecodable file is rejected with an Uzbek message', async ({ page }, testInfo) => {
  const device = testInfo.project.name.replace(/\s+/g, '-');
  await page.goto('/');

  await page.locator('input[type="file"]').first().setInputFiles({
    name: 'broken.jpg',
    mimeType: 'image/jpeg',
    buffer: Buffer.from('this is not an image at all'),
  });

  await expect(
    page.getByText("Rasmni o'qib bo'lmadi. Boshqa rasm bilan urinib ko'ring."),
  ).toBeVisible();
  await page.screenshot(shot(`${device}-14-bad-image`));
  await expectNoHorizontalScroll(page);
});

test('large photos are downscaled to 1280px before upload', async ({ page }) => {
  await page.goto('/');

  const uploaded = page.waitForRequest((request) => request.url().includes('/api/analyze'));
  const buffer = await makeJpeg(page, 3000);
  await page
    .locator('input[type="file"]')
    .first()
    .setInputFiles({ name: 'huge.jpg', mimeType: 'image/jpeg', buffer });
  await page.getByRole('button', { name: 'Tahlil qilish' }).click();
  await uploaded;

  // Read back what the server stored via the saved scan's image.
  await expect(page.getByRole('button', { name: 'Yangi tahlil' })).toBeVisible({
    timeout: 20_000,
  });

  const longest = await page.evaluate(async () => {
    const list = await (await fetch('/api/scans?limit=1')).json();
    const blob = await (await fetch(`/api/scans/${list.scans[0].id}/image`)).blob();
    const bitmap = await createImageBitmap(blob);
    return Math.max(bitmap.width, bitmap.height);
  });
  expect(longest).toBe(1280);
});
