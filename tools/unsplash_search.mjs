// usage: node usearch.mjs out.json "query1" "query2" ...  (free-licence results only)
import { chromium } from '/opt/node-tools/node_modules/playwright/index.mjs';
import fs from 'fs';
const [out, ...queries] = process.argv.slice(2);
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
const page = await browser.newPage({ viewport: { width: 1400, height: 3000 }, userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Safari/537.36' });
const results = fs.existsSync(out) ? JSON.parse(fs.readFileSync(out)) : {};
for (const q of queries) {
  await page.goto(`https://unsplash.com/s/photos/${encodeURIComponent(q.replace(/ /g, '-'))}?license=free&orientation=portrait`, { waitUntil: 'domcontentloaded', timeout: 90000 });
  for (let i = 0; i < 30 && (await page.title()).includes('bot'); i++) await page.waitForTimeout(2000);
  await page.waitForTimeout(4000);
  results[q] = await page.evaluate(() => {
    const seen = new Set(), list = [];
    for (const a of document.querySelectorAll('figure a[href^="/photos/"]')) {
      const href = a.getAttribute('href'); if (seen.has(href)) continue; seen.add(href);
      const fig = a.closest('figure'); const img = fig?.querySelector('img[src*="images.unsplash.com/photo"]');
      if (!img) continue;
      const plus = !!fig.querySelector('a[href*="/plus"]') || img.src.includes('plus.unsplash');
      list.push({ href, alt: img.alt, src: img.src.split('?')[0], plus });
    }
    return list;
  });
  console.error(q, results[q].length);
}
fs.writeFileSync(out, JSON.stringify(results, null, 1));
await browser.close();
