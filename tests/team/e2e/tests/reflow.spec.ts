import { expect, test } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { LIBRARIAN, READER, signIn } from './helpers';

// Reflow check: does a page fit the window width, or does content run past the right edge?
// Widths: 872 px is about 200% browser zoom on a 1744 px window; 640 px is about 200% on a
// 1280 px window; 320 px is the WCAG 1.4.10 reference width (400% zoom on 1280 px).
// Start from the baseline: `npm run reset`, then `npm run a11y`.
// Results (every page and width) are written to tests/team/evidence/usability/reflow-results.json.

const WIDTHS = [872, 640, 320];
const PAGES = [
  { name: 'login page', account: null, path: '/authentication/login/' },
  { name: 'books catalogue', account: LIBRARIAN, path: '/book/' },
  { name: 'lend form', account: LIBRARIAN, path: '/order/lend/' },
  { name: 'all orders', account: LIBRARIAN, path: '/order/all/' },
  { name: 'my orders', account: READER, path: '/order/my/' },
  // The return confirmation page is reached from All Orders (needs an open loan: use the baseline).
  { name: 'return page', account: LIBRARIAN, path: '/order/all/', openReturnPage: true },
];

type Result = { page: string; width: number; contentWidth: number; windowWidth: number; fits: boolean; widestElements: string[] };
const results: Result[] = [];

test.afterAll(() => {
  const dir = path.resolve(__dirname, '..', '..', 'evidence', 'usability');
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(
    path.join(dir, 'reflow-results.json'),
    JSON.stringify({ run: new Date().toISOString(), results }, null, 2),
  );
});

test.describe('Reflow at narrow widths', () => {
  for (const width of WIDTHS) {
    for (const p of PAGES) {
      test(`${p.name} at ${width} px`, async ({ page }) => {
        await page.setViewportSize({ width, height: 800 });
        if (p.account) await signIn(page, p.account);
        await page.goto(p.path);
        if (p.openReturnPage) {
          await page.getByRole('link', { name: /Record Return/ }).first().click();
          await expect(page.getByRole('button', { name: 'Yes, Record the Return' })).toBeVisible();
        }

        const measured = await page.evaluate(() => {
          const windowWidth = document.documentElement.clientWidth;
          const contentWidth = Math.max(document.documentElement.scrollWidth, document.body.scrollWidth);
          const widest = Array.from(document.querySelectorAll('body *'))
            .filter((el) => {
              const r = el.getBoundingClientRect();
              return r.width > 0 && r.right > windowWidth + 1;
            })
            .slice(0, 8)
            .map((el) => {
              const cls = typeof el.className === 'string' ? el.className.trim().split(/\s+/).slice(0, 3).join('.') : '';
              return el.tagName.toLowerCase() + (el.id ? `#${el.id}` : '') + (cls ? `.${cls}` : '');
            });
          return { windowWidth, contentWidth, widest };
        });

        const fits = measured.contentWidth <= measured.windowWidth + 1;
        results.push({
          page: p.name,
          width,
          contentWidth: measured.contentWidth,
          windowWidth: measured.windowWidth,
          fits,
          widestElements: measured.widest,
        });
        expect(
          measured.contentWidth,
          `${p.name} at ${width} px: content is ${measured.contentWidth} px wide in a ${measured.windowWidth} px window (${measured.widest.join(', ')})`,
        ).toBeLessThanOrEqual(measured.windowWidth + 1);
      });
    }
  }
});
