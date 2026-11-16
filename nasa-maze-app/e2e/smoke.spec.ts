import { expect, test } from '@playwright/test'

test('loads the map and shows a route summary', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByTestId('mars-map')).toBeVisible()
  await expect(page.getByTestId('route-panel')).toBeVisible()

  const find = page.getByRole('button', { name: /find route/i })
  await expect(find).toBeEnabled({ timeout: 30_000 })
  await find.click()

  await expect(page.getByTestId('route-summary')).toBeVisible({ timeout: 90_000 })
  await expect(page.locator('path.leaflet-interactive').first()).toBeVisible()

  await page.getByRole('button', { name: /new route/i }).click()
  await expect(page.getByTestId('route-panel')).toBeVisible()
})

test('shows the Offline basemap badge when the tile host is blocked', async ({ page, baseURL }) => {
  await page.route('**/*', (route) =>
    route.request().url().startsWith(baseURL!) ? route.continue() : route.abort(),
  )
  await page.goto('/')
  await expect(page.getByTestId('status-badges')).toContainText(/offline/i, { timeout: 30_000 })
})
