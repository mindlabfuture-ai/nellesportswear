// Rasterise images/svg/*.svg -> images/png (black bg) and images/png-transparent
import { chromium } from '/opt/node-tools/node_modules/playwright/index.mjs';
import fs from 'fs';
import path from 'path';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..', 'images');
const src = path.join(root, 'svg');
fs.mkdirSync(path.join(root, 'png'), { recursive: true });
fs.mkdirSync(path.join(root, 'png-transparent'), { recursive: true });

const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
const page = await browser.newPage({ viewport: { width: 1000, height: 1250 } });
for (const f of fs.readdirSync(src).filter((f) => f.endsWith('.svg'))) {
  const transparent = f.includes('.transparent');
  await page.setContent(`<body style="margin:0;background:transparent">${fs.readFileSync(path.join(src, f), 'utf8')}</body>`);
  const out = path.join(root, transparent ? 'png-transparent' : 'png', f.replace('.transparent', '').replace('.svg', '.png'));
  await page.screenshot({ path: out, omitBackground: transparent });
  console.log('wrote', out);
}
await browser.close();
