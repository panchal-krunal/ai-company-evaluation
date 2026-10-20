import { expect, test } from '@playwright/test'

test('dashboard shell loads', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Companies' })).toBeVisible()
})
