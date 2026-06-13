/**
 * WebScraper.js - Drop-in replacement: Playwright → patchright
 *
 * Based on the 2025-26 Cloudflare bypass brief (notes.md §Cloudflare 2025-26):
 * - Primary: patchright (drop-in Playwright replacement) - patches CDP leaks
 *   (Runtime.enable, Console.enable, Command Flags, Closed Shadow Roots)
 * - Auto-fallback: camoufox (Firefox) if patchright fails or platform unsupported
 *
 * Usage:
 *   import { scrape } from './WebScraper.js';
 *   const data = await scrape('https://example.com', { selector: 'h1' });
 */

let browserImpl = null;
let browserType = 'unknown';

async function launchBrowser() {
  // Try patchright first (Chromium drop-in)
  try {
    const { chromium } = await import('patchright');
    const browser = await chromium.launch({
      headless: true,
      args: [
        '--disable-blink-features=AutomationControlled',
        '--disable-features=IsolateOrigins,site-per-process',
        '--no-sandbox',
        '--disable-setuid-sandbox',
      ],
    });
    browserImpl = browser;
    browserType = 'patchright';
    console.log('✅ patchright launched');
    return browser;
  } catch (e) {
    console.warn(`⚠️ patchright failed: ${e.message}`);
    console.log('   falling back to camoufox (Firefox)...');
  }

  // Fallback: camoufox (Firefox-based, better anti-detection)
  try {
    const { launch } = await import('camoufox');
    const browser = await launch({
      headless: true,
      args: ['--no-sandbox'],
    });
    browserImpl = browser;
    browserType = 'camoufox';
    console.log('✅ camoufox launched (Firefox)');
    return browser;
  } catch (e) {
    throw new Error(`Both patchright and camoufox failed: ${e.message}`);
  }
}

async function getContext(browser) {
  // Use the right API based on browser type
  if (browserType === 'camoufox') {
    return browser;  // camoufox returns context-like object directly
  }
  return browser.newContext({
    userAgent: 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    viewport: { width: 1920, height: 1080 },
    locale: 'en-US',
    timezoneId: 'America/New_York',
    extraHTTPHeaders: {
      'Accept-Language': 'en-US,en;q=0.9',
    },
  });
}

async function getPage(context) {
  if (browserType === 'camoufox') {
    return context.newPage();
  }
  return context.newPage();
}

/**
 * Main scrape function - drop-in replacement for the old Playwright version.
 * @param {string} url - Target URL
 * @param {object} options - { selector?, waitFor?, retries? }
 */
export async function scrape(url, options = {}) {
  const { selector, waitFor, retries = 3 } = options;

  const browser = await launchBrowser();
  const context = await getContext(browser);
  const page = await getPage(context);

  try {
    let lastErr;
    for (let i = 0; i < retries; i++) {
      try {
        await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
        if (waitFor) {
          await page.waitForSelector(waitFor, { timeout: 15000 });
        }
        if (selector) {
          const data = await page.$$eval(selector, els => els.map(e => e.innerText));
          return { ok: true, browser: browserType, data, count: data.length };
        }
        const title = await page.title();
        const html = await page.content();
        return { ok: true, browser: browserType, title, html };
      } catch (e) {
        lastErr = e;
        if (i < retries - 1) {
          await new Promise(r => setTimeout(r, 1000 * (i + 1)));  // exponential backoff
        }
      }
    }
    return { ok: false, browser: browserType, error: lastErr?.message };
  } finally {
    if (browserType === 'patchright' && browserImpl) {
      await browserImpl.close();
    } else if (browserType === 'camoufox' && browserImpl) {
      await browserImpl.close();
    }
  }
}

// CLI usage
if (import.meta.url === `file://${process.argv[1]}`) {
  const url = process.argv[2];
  if (!url) {
    console.log('Usage: node WebScraper.js <url> [selector]');
    process.exit(1);
  }
  const selector = process.argv[3];
  scrape(url, { selector }).then(r => {
    console.log(JSON.stringify(r, null, 2));
  });
}
