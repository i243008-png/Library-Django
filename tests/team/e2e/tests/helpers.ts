import { expect, Page } from '@playwright/test';

export const LIBRARIAN = { email: 'librarian@library.com', password: 'admin123password' };
export const READER = { email: 'reader@library.com', password: 'reader123password' };

// Sign in through the login page (seeded demo accounts, see BASELINE.md).
export async function signIn(page: Page, account: { email: string; password: string }) {
  await page.goto('/authentication/login/');
  await page.getByLabel('Email Address').fill(account.email);
  await page.getByLabel('Password').fill(account.password);
  await page.getByRole('button', { name: 'Sign In' }).click();
  await expect(page).not.toHaveURL(/\/authentication\/login\//);
}

// A due date as the app shows it ("6 Dec 2026"), in the app's time zone.
export function dueDate(days: number): string {
  const parts = new Intl.DateTimeFormat('en-US', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: 'Europe/Kyiv',
  }).formatToParts(new Date(Date.now() + days * 86_400_000));
  const get = (type: string) => parts.find((p) => p.type === type)!.value;
  return `${get('day')} ${get('month')} ${get('year')}`;
}

// Available copies of a book, read from its detail page badge ("7 of 7 Available").
export async function availableCopies(page: Page, bookName: string): Promise<number> {
  await page.goto('/book/');
  await page.getByRole('link', { name: bookName }).first().click();
  const badge = await page.getByText(/\d+ of \d+ Available/).first().textContent();
  return Number(/(\d+) of \d+ Available/.exec(badge ?? '')![1]);
}

// Display labels of the seeded accounts in the lend form's Reader dropdown.
export const BOB = 'Bob Williams (bob@library.com)';
export const ALICE = 'Alice Smith (alice@library.com)';
export const OLEH = 'Oleh Melnyk (reader@library.com)';

// Fill in and submit the Lend Directly form. Pass `days` only to change the default of 14.
export async function fillLendForm(page: Page, reader: string, book: string, days?: number) {
  await page.goto('/order/lend/');
  await page.getByLabel('Reader').selectOption({ label: reader });
  await page.getByLabel('Book').selectOption({ label: book });
  if (days !== undefined) {
    await page.getByLabel('Loan Duration (Days)').fill(String(days));
  }
  await page.getByRole('button', { name: 'Lend Book' }).click();
}

// API helpers for test set-up. They use the signed-in session and its CSRF token.
export async function apiList(page: Page, url: string): Promise<any[]> {
  const response = await page.request.get(url);
  expect(response.ok()).toBeTruthy();
  const body = await response.json();
  return Array.isArray(body) ? body : body.results;
}

async function csrfToken(page: Page): Promise<string> {
  const cookies = await page.context().cookies();
  return cookies.find((c) => c.name === 'csrftoken')?.value ?? '';
}

export async function apiSend(page: Page, method: 'POST' | 'PATCH', url: string, data: object) {
  const response = await page.request.fetch(url, {
    method,
    data,
    headers: { 'X-CSRFToken': await csrfToken(page) },
  });
  expect(response.ok(), `${method} ${url} -> ${response.status()}`).toBeTruthy();
  return response.json();
}

export async function idOfBook(page: Page, name: string): Promise<number> {
  const books = await apiList(page, '/api/v1/book/');
  return books.find((b) => b.name === name)!.id;
}

export async function idOfUser(page: Page, email: string): Promise<number> {
  const users = await apiList(page, '/api/v1/user/');
  return users.find((u) => u.email === email)!.id;
}
