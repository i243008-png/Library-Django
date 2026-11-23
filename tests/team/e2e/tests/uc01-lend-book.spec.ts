import { expect, test } from '@playwright/test';
import {
  ALICE,
  BOB,
  LIBRARIAN,
  OLEH,
  READER,
  apiSend,
  availableCopies,
  dueDate,
  fillLendForm,
  idOfBook,
  idOfUser,
  signIn,
} from './helpers';

// UC-01 Lend a book to a reader (tests/team/usecases/USE_CASES.md).
// The tests run in order and share one database, so start from the baseline:
// `npm run reset`, then `npm test`.

const CLEAN_CODE = 'Clean Code: A Handbook of Agile Software Craftsmanship';

test.describe.configure({ mode: 'serial' });

test.describe('UC-01 Lend a book to a reader', () => {
  test('MF: librarian lends Animal Farm to Bob for 14 days', async ({ page }) => {
    await signIn(page, LIBRARIAN);
    const before = await availableCopies(page, 'Animal Farm');

    await page.goto('/order/lend/');
    await expect(page.getByRole('heading', { name: 'Lend Directly' })).toBeVisible();
    await page.getByLabel('Reader').selectOption({ label: BOB });
    await page.getByLabel('Book').selectOption({ label: 'Animal Farm' });
    await page.getByLabel('Loan Duration (Days)').fill('14');
    await page.getByRole('button', { name: 'Lend Book' }).click();

    await expect(page).toHaveURL(/\/order\/all\/$/);
    await expect(page.getByRole('status')).toContainText(
      `Lent “Animal Farm” to Bob Williams, due ${dueDate(14)}.`,
    );
    const row = page
      .getByRole('row')
      .filter({ hasText: 'bob@library.com' })
      .filter({ hasText: 'Animal Farm' });
    await expect(row).toContainText('Pending return');
    await expect(row.getByRole('link', { name: /Record Return/ })).toBeVisible();

    expect(await availableCopies(page, 'Animal Farm')).toBe(before - 1);
  });

  test('AF1: a one-day loan is accepted', async ({ page }) => {
    await signIn(page, LIBRARIAN);
    const before = await availableCopies(page, 'Animal Farm');

    await fillLendForm(page, ALICE, 'Animal Farm', 1);

    await expect(page.getByRole('status')).toContainText(
      `Lent “Animal Farm” to Alice Smith, due ${dueDate(1)}.`,
    );
    expect(await availableCopies(page, 'Animal Farm')).toBe(before - 1);
  });

  test('AF2: a 30-day loan is accepted', async ({ page }) => {
    await signIn(page, LIBRARIAN);
    const before = await availableCopies(page, 'Animal Farm');

    await fillLendForm(page, OLEH, 'Animal Farm', 30);

    await expect(page.getByRole('status')).toContainText(
      `Lent “Animal Farm” to Oleh Melnyk, due ${dueDate(30)}.`,
    );
    expect(await availableCopies(page, 'Animal Farm')).toBe(before - 1);
  });

  test('AF3: lending starts from the book page with the book preselected', async ({ page }) => {
    await signIn(page, LIBRARIAN);
    const before = await availableCopies(page, '1984');

    await page.goto('/book/');
    await page.getByRole('link', { name: '1984' }).first().click();
    await page.getByRole('link', { name: 'Lend Directly' }).click();
    await expect(page).toHaveURL(/\/order\/lend\/\?book=\d+/);
    await expect(page.getByLabel('Book').locator('option:checked')).toHaveText('1984');

    await page.getByLabel('Reader').selectOption({ label: BOB });
    await page.getByRole('button', { name: 'Lend Book' }).click();

    await expect(page.getByRole('status')).toContainText(
      `Lent “1984” to Bob Williams, due ${dueDate(14)}.`,
    );
    expect(await availableCopies(page, '1984')).toBe(before - 1);
  });

  test('EF1: 0 days is stopped by the form', async ({ page }) => {
    await signIn(page, LIBRARIAN);
    const before = await availableCopies(page, 'Animal Farm');

    await fillLendForm(page, ALICE, 'Animal Farm', 0);

    await expect(page).toHaveURL(/\/order\/lend\//);
    const message = await page
      .getByLabel('Loan Duration (Days)')
      .evaluate((el: HTMLInputElement) => el.validationMessage);
    expect(message).toMatch(/greater than or equal to 1/);
    expect(await availableCopies(page, 'Animal Farm')).toBe(before);
  });

  test('EF2: 31 days is stopped by the form', async ({ page }) => {
    await signIn(page, LIBRARIAN);
    const before = await availableCopies(page, 'Animal Farm');

    await fillLendForm(page, ALICE, 'Animal Farm', 31);

    await expect(page).toHaveURL(/\/order\/lend\//);
    const message = await page
      .getByLabel('Loan Duration (Days)')
      .evaluate((el: HTMLInputElement) => el.validationMessage);
    expect(message).toMatch(/less than or equal to 30/);
    expect(await availableCopies(page, 'Animal Farm')).toBe(before);
  });

  test('EF3: a reader with an overdue loan is refused', async ({ page }) => {
    await signIn(page, LIBRARIAN);
    // Set-up through the API: an open loan of Clean Code for Oleh that was due 5 days ago.
    await apiSend(page, 'POST', '/api/v1/order/', {
      user: await idOfUser(page, 'reader@library.com'),
      book: await idOfBook(page, CLEAN_CODE),
      plated_end_at: new Date(Date.now() - 5 * 86_400_000).toISOString(),
    });
    const before = await availableCopies(page, 'The Adventures of Sherlock Holmes');

    await fillLendForm(page, OLEH, 'The Adventures of Sherlock Holmes');

    await expect(page).toHaveURL(/\/order\/lend\//);
    await expect(
      page.getByText(
        `Oleh Melnyk has an overdue loan: “${CLEAN_CODE}”, due ${dueDate(-5)}. It must be returned first.`,
      ),
    ).toBeVisible();
    expect(await availableCopies(page, 'The Adventures of Sherlock Holmes')).toBe(before);
  });

  test('EF4: a reader who already has the book is refused', async ({ page }) => {
    await signIn(page, LIBRARIAN);
    const before = await availableCopies(page, '1984');

    // Alice holds 1984 at the baseline.
    await fillLendForm(page, ALICE, '1984');

    await expect(page).toHaveURL(/\/order\/lend\//);
    await expect(page.getByText('Alice Smith already has “1984” on loan.')).toBeVisible();
    expect(await availableCopies(page, '1984')).toBe(before);
  });

  test('EF5: no copy available is refused', async ({ page }) => {
    await signIn(page, LIBRARIAN);
    // Set-up through the API: Zakhar Berkut is reduced to one copy, then lent to Bob.
    const book = 'Zakhar Berkut';
    await apiSend(page, 'PATCH', `/api/v1/book/${await idOfBook(page, book)}/`, { count: 1 });
    await fillLendForm(page, BOB, book);
    await expect(page.getByRole('status')).toContainText(`Lent “${book}” to Bob Williams`);
    expect(await availableCopies(page, book)).toBe(0);

    await fillLendForm(page, ALICE, book);

    await expect(page).toHaveURL(/\/order\/lend\//);
    await expect(
      page.getByText(
        `No copy of “${book}” is available. A reservation may be holding the last one.`,
      ),
    ).toBeVisible();
    expect(await availableCopies(page, book)).toBe(0);
  });

  test('EF6: a reader cannot open the lend page', async ({ page }) => {
    await signIn(page, READER);

    const response = await page.goto('/order/lend/');

    expect(response?.status()).toBe(404);
    await expect(page.getByText('Page not found')).toBeVisible();
  });
});
