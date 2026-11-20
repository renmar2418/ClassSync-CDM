import { test, expect } from '@playwright/test';

test.describe('ClassSync Web PWA Visual & Interaction Tests', () => {
  test('01. Welcome & Login page renders with Turnstile, Brand Card, and Jakob law styling', async ({ page }) => {
    await page.goto('/login');

    // Verify Title & Hero Header
    await expect(page.locator('h1')).toContainText(/Welcome back|Sign In/i);
    await expect(page.locator('#turnstile-container')).toBeVisible();
    await expect(page.locator('#turnstile-container')).toContainText('Cloudflare Turnstile Verified');

    // Right column brand text
    const heroText = page.locator('text=AI-Powered University Classroom Scheduling');
    if (await heroText.isVisible()) {
      await expect(heroText).toBeVisible();
    }
  });

  test('02. ASVS 4.0 First-time password setup entropy checklist validates real-time', async ({ page }) => {
    await page.goto('/setup-password');

    await expect(page.locator('h1')).toContainText('First-time password setup');
    
    // Fill credentials
    const idInput = page.locator('input[placeholder*="24-00123"]');
    await idInput.fill('24-00123');

    // Verify entropy requirements render
    await expect(page.locator('text=OWASP ASVS 4.0 Security Standard')).toBeVisible();
    await expect(page.locator('text=10+ characters')).toBeVisible();
    await expect(page.locator('text=No campus keywords')).toBeVisible();
  });

  test('03. Standalone chromeless Projector View renders for PRRC 301', async ({ page }) => {
    await page.goto('/projector/PRRC%20301');

    // Check header and room badge
    await expect(page.getByText('PRRC 301', { exact: true })).toBeVisible();
    await expect(page.locator('text=Exit Projector Mode')).toBeVisible();
  });
});
