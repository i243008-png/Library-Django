import { expect, test, Page } from '@playwright/test';
import {
  LIBRARIAN,
  READER,
  apiList,
  apiSend,
  availableCopies,
  idOfBook,
  idOfUser,
  signIn,
} from './helpers';

// UC-02 Record the return of a book (tests/team/usecases/USE_CASES.md).
// The tests run in order and share one database, so start from the baseline:
// `npm run reset`, then `npm test`.

const SHERLOCK = 'The Adventures of Sherlock Holmes';
const CLEAN_CODE = 'Clean Code: A Handbook of Agile Software Craftsmanship';

test.describe.configure({ mode: 'serial' });

// The row of an open loan on All Orders (desktop table: "Pending return").
function openLoanRow(page: Page, email: string, book: string) {
  return page
    .getByRole('row')
    .filter({ hasText: email })
    .filter({ hasText: book })
    .filter({ hasText: 'Pending return' })
    .first();
}

test.describe('UC-02 Record the return of a book', () => {
  test('MF: librarian records the return of the Kobzar loan', async ({ page }) => {
    await signIn(page, LIBRARIAN);
    const before = await availableCopies(page, 'Kobzar');

    await page.goto('/order/all/');
    await openLoanRow(page, 'reader@library.com', 'Kobzar')
      .getByRole('link', { name: /Record Return/ })
      .click();
    await expect(page.getByText('Record the return of “Kobzar”?')).toBeVisible();
    await page.getByRole('button', { name: 'Yes, Record the Return' }).click();

    await expect(page).toHaveURL(/\/order\/all\/$/);
    await expect(page.getByRole('status')).toContainText(
      /Return recorded: “Kobzar” is back in stock, and loan #\d+ is closed\./,
    );
    const row = page
      .getByRole('row')
      .filter({ hasText: 'reader@library.com' })
      .filter({ hasText: 'Kobzar' });
    await expect(row).toContainText('Closed');
    await expect(row.getByRole('link', { name: /Record Return/ })).toHaveCount(0);

    expect(await availableCopies(page, 'Kobzar')).toBe(before + 1);
  });

  test('AF1: "Not Now" leaves the loan open', async ({ page }) => {
    await signIn(page, LIBRARIAN);
    const before = await availableCopies(page, '1984');

    await page.goto('/order/all/');
    await openLoanRow(page, 'alice@library.com', '1984')
      .getByRole('link', { name: /Record Return/ })
      .click();
    await page.getByRole('link', { name: 'Not Now' }).click();

    await expect(page).toHaveURL(/\/order\/all\/$/);
    await expect(openLoanRow(page, 'alice@library.com', '1984')).toBeVisible();
    expect(await availableCopies(page, '1984')).toBe(before);
  });

  test('AF2: the return of an overdue loan is recorded', async ({ page }) => {
    await signIn(page, LIBRARIAN);
    // Set-up through the API: an open loan of Sherlock Holmes for Bob that was due 5 days ago.
    await apiSend(page, 'POST', '/api/v1/order/', {
      user: await idOfUser(page, 'bob@library.com'),
      book: await idOfBook(page, SHERLOCK),
      plated_end_at: new Date(Date.now() - 5 * 86_400_000).toISOString(),
    });
    const before = await availableCopies(page, SHERLOCK);

    await page.goto('/order/all/');
    await openLoanRow(page, 'bob@library.com', SHERLOCK)
      .getByRole('link', { name: /Record Return/ })
      .click();
    await page.getByRole('button', { name: 'Yes, Record the Return' }).click();

    await expect(page.getByRole('status')).toContainText(
      /Return recorded: “The Adventures of Sherlock Holmes” is back in stock, and loan #\d+ is closed\./,
    );
    await expect(openLoanRow(page, 'bob@library.com', SHERLOCK)).toHaveCount(0);
    expect(await availableCopies(page, SHERLOCK)).toBe(before + 1);
  });

  test('AF3: the reader sees the returned loan in My Orders', async ({ page }) => {
    // The Kobzar loan of reader@library.com was returned in the main flow.
    await signIn(page, READER);

    await page.goto('/order/my/');

    await expect(page.getByRole('heading', { name: 'My Borrowed Books' })).toBeVisible();
    const row = page.getByRole('row').filter({ hasText: 'Kobzar' });
    await expect(row).toContainText('Returned');
  });

  test('EF1: a closed loan is shown as already closed', async ({ page }) => {
    await signIn(page, LIBRARIAN);
    // The seeded returned loan: Bob, Clean Code.
    const bob = await idOfUser(page, 'bob@library.com');
    const cleanCode = await idOfBook(page, CLEAN_CODE);
    const orders = await apiList(page, '/api/v1/order/');
    const closed = orders.find((o) => o.user === bob && o.book === cleanCode && o.end_at);
    const before = await availableCopies(page, CLEAN_CODE);

    await page.goto(`/order/close/${closed!.id}/`);

    await expect(page.getByText(/This loan was already closed on .+\./)).toBeVisible();
    await expect(page.getByRole('button', { name: 'Yes, Record the Return' })).toHaveCount(0);
    await expect(page.getByRole('link', { name: 'Back to All Orders' })).toBeVisible();
    expect(await availableCopies(page, CLEAN_CODE)).toBe(before);
  });

  test('EF2: a second submit of the same return changes nothing', async ({ page, context }) => {
    await signIn(page, LIBRARIAN);
    const before = await availableCopies(page, '1984');

    // Open the same confirmation page in two tabs.
    await page.goto('/order/all/');
    await openLoanRow(page, 'alice@library.com', '1984')
      .getByRole('link', { name: /Record Return/ })
      .click();
    const url = page.url();
    const id = /\/order\/close\/(\d+)\//.exec(url)![1];
    const second = await context.newPage();
    await second.goto(url);

    // First tab: the return is recorded.
    await page.getByRole('button', { name: 'Yes, Record the Return' }).click();
    await expect(page.getByRole('status')).toContainText('Return recorded: “1984”');
    const afterFirst = await availableCopies(page, '1984');
    expect(afterFirst).toBe(before + 1);

    // Second tab: the same form is submitted again.
    await second.getByRole('button', { name: 'Yes, Record the Return' }).click();
    await expect(second.getByRole('status')).toContainText(
      `Loan #${id} was already closed, so nothing changed.`,
    );
    expect(await availableCopies(second, '1984')).toBe(afterFirst);
  });

  test('EF3: a reader cannot open the return page', async ({ page }) => {
    await signIn(page, LIBRARIAN);
    // Any open loan will do: Bob's Animal Farm loan from UC-01 (or any other open loan).
    const orders = await apiList(page, '/api/v1/order/');
    const open = orders.find((o) => !o.end_at);
    expect(open, 'an open loan is needed').toBeTruthy();

    await page.context().clearCookies();
    await signIn(page, READER);
    const before = await availableCopies(page, 'Animal Farm');
    const response = await page.goto(`/order/close/${open!.id}/`);

    expect(response?.status()).toBe(404);
    await expect(page.getByText('Page not found')).toBeVisible();
    expect(await availableCopies(page, 'Animal Farm')).toBe(before);
  });

  test('EF4: a loan that does not exist gives the 404 page', async ({ page }) => {
    await signIn(page, LIBRARIAN);

    const response = await page.goto('/order/close/999999/');

    expect(response?.status()).toBe(404);
    await expect(page.getByText('Page not found')).toBeVisible();
  });
});
