import { AxeBuilder } from '@axe-core/playwright';
import { expect, test, Page } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { ALICE, LIBRARIAN, READER, fillLendForm, signIn } from './helpers';

// Accessibility scans with axe-core (WCAG 2.0, 2.1 and 2.2, levels A and AA) of the pages used by
// UC-01 and UC-02, for each role. Start from the baseline: `npm run reset`, then `npm run a11y`.
// A test fails on a critical or serious violation. Every violation, whatever its impact, is
// written to tests/team/evidence/accessibility/axe-results.json.

const TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];

type Finding = { page: string; rule: string; impact: string | null | undefined; help: string; targets: string[] };
type Coverage = { page: string; rulesPassed: number; rulesNotApplicable: number; needsReview: { rule: string; elements: string[] }[] };
const findings: Finding[] = [];
const checked: Coverage[] = [];

async function scan(page: Page, name: string) {
  await page.evaluate(() => document.fonts.ready);
  const result = await new AxeBuilder({ page }).withTags(TAGS).analyze();
  // Coverage shows that the scan really ran: how many rules passed, and which ones axe could not
  // decide on its own ("incomplete") and that therefore need a manual look.
  checked.push({
    page: name,
    rulesPassed: result.passes.length,
    rulesNotApplicable: result.inapplicable.length,
    needsReview: result.incomplete.map((v) => ({
      rule: v.id,
      elements: v.nodes.map((n) => n.target.join(' ')),
    })),
  });
  for (const v of result.violations) {
    findings.push({
      page: name,
      rule: v.id,
      impact: v.impact,
      help: v.help,
      targets: v.nodes.map((n) => n.target.join(' ')),
    });
  }
  const blocking = result.violations.filter((v) => v.impact === 'critical' || v.impact === 'serious');
  expect(
    blocking.map((v) => `${v.id} (${v.impact}): ${v.help}`),
    `${name}: critical or serious violations`,
  ).toEqual([]);
}

test.describe.configure({ mode: 'serial' });

test.afterAll(() => {
  const dir = path.resolve(__dirname, '..', '..', 'evidence', 'accessibility');
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(
    path.join(dir, 'axe-results.json'),
    JSON.stringify({ run: new Date().toISOString(), tags: TAGS, coverage: checked, findings }, null, 2),
  );
});

test.describe('Accessibility (axe-core)', () => {
  test('login page (anonymous)', async ({ page }) => {
    await page.goto('/authentication/login/');
    await scan(page, 'login page');
  });

  test('books catalogue (librarian)', async ({ page }) => {
    await signIn(page, LIBRARIAN);
    await page.goto('/book/');
    await scan(page, 'books catalogue');
  });

  test('Lend Directly form (librarian)', async ({ page }) => {
    await signIn(page, LIBRARIAN);
    await page.goto('/order/lend/');
    await scan(page, 'lend form');
  });

  test('Lend Directly form with a refusal message (librarian)', async ({ page }) => {
    await signIn(page, LIBRARIAN);
    // Alice already holds 1984 at the baseline, so the form comes back with an error.
    await fillLendForm(page, ALICE, '1984');
    await expect(page.getByText('Alice Smith already has “1984” on loan.')).toBeVisible();
    await scan(page, 'lend form with error');
  });

  test('Lend Directly form at 375 px wide (librarian)', async ({ page }) => {
    await signIn(page, LIBRARIAN);
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/order/lend/');
    await scan(page, 'lend form at 375 px');
  });

  test('All Orders (librarian)', async ({ page }) => {
    await signIn(page, LIBRARIAN);
    await page.goto('/order/all/');
    await scan(page, 'all orders');
  });

  test('return confirmation page (librarian)', async ({ page }) => {
    await signIn(page, LIBRARIAN);
    await page.goto('/order/all/');
    await page.getByRole('link', { name: /Record Return/ }).first().click();
    await expect(page.getByRole('button', { name: 'Yes, Record the Return' })).toBeVisible();
    await scan(page, 'return confirmation');
  });

  test('My Borrowed Books (reader)', async ({ page }) => {
    await signIn(page, READER);
    await page.goto('/order/my/');
    await scan(page, 'my orders');
  });

  test('404 page (reader opens a librarian page)', async ({ page }) => {
    await signIn(page, READER);
    const response = await page.goto('/order/lend/');
    expect(response?.status()).toBe(404);
    await scan(page, '404 page');
  });
});
