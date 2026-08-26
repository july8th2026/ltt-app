// Soi khu /developers bang trinh duyet that.
//
// Chup anh + do ba thu mot anh chup KHONG noi duoc: be rong that su duoc dung,
// loi console, va tran ngang cua tai lieu.
//
//   node tools/qa/dev_portal_qa.mjs <thu-muc-ra> [--base http://127.0.0.1:8101]
import { chromium } from 'playwright';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const out = process.argv[2] || 'docs/developer_portal_mvp_ui/evidence';
const bi = process.argv.indexOf('--base');
const BASE = bi > -1 ? process.argv[bi + 1] : 'http://127.0.0.1:8101';
const EMAIL = 'dev-ui-qa@example.com', PASS = 'a-good-password-12';

const TRANG = [
  ['overview', '/developers'],
  ['keys', '/developers/keys'],
  ['projects', '/developers/projects'],
  ['logs', '/developers/logs'],
  ['jobs', '/developers/jobs'],
  ['usage', '/developers/usage'],
  ['tools', '/developers/tools'],
  ['playground', '/developers/playground'],
  ['pricing', '/developers/pricing'],
  ['quickstart', '/developers/quickstart'],
  ['cli', '/developers/cli'],
  ['docs', '/developers/docs'],
  ['webhooks', '/developers/webhooks'],
  ['settings', '/developers/settings'],
  ['privacy', '/developers/privacy'],
  ['notifications', '/developers/notifications'],
];
const KHUNG = [['1920', 1920, 1080], ['1440', 1440, 900], ['1280', 1280, 800],
               ['1024', 1024, 768], ['768', 768, 1024], ['390', 390, 844]];
const CHINH = new Set(['overview', 'keys', 'logs', 'quickstart', 'tools', 'pricing']);

const bao = [];

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
const page = await ctx.newPage();

const loi = [];
page.on('console', m => { if (m.type() === 'error') loi.push(`${page.url()} :: ${m.text()}`); });
page.on('pageerror', e => loi.push(`${page.url()} :: PAGEERROR ${e.message}`));
const mang = [];
page.on('response', r => { if (r.status() >= 400) mang.push(`${r.status()} ${r.url()}`); });

await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' });
await page.fill('input[name=username]', EMAIL);
await page.fill('input[name=password]', PASS);
await Promise.all([page.waitForNavigation({ waitUntil: 'networkidle' }),
                   page.click('button[type=submit]')]);
if (page.url().includes('/login')) { console.error('DANG NHAP THAT BAI'); process.exit(1); }

for (const [nhan, w, h] of KHUNG) {
  await page.setViewportSize({ width: w, height: h });
  mkdirSync(join(out, nhan), { recursive: true });
  for (const [ten, duong] of TRANG) {
    if (w !== 1920 && w !== 390 && !CHINH.has(ten)) continue;
    await page.goto(BASE + duong, { waitUntil: 'networkidle' });
    const d = await page.evaluate(() => {
      const main = document.querySelector('.app-main');
      const shell = document.querySelector('.app-shell');
      const pg = document.querySelector('main.page, main[class*=page]');
      const r = el => el ? Math.round(el.getBoundingClientRect().width) : null;
      // Phan tu nao dang lam tai lieu rong hon khung nhin.
      const tran = [];
      if (document.documentElement.scrollWidth > window.innerWidth + 1) {
        for (const el of document.querySelectorAll('body *')) {
          const b = el.getBoundingClientRect();
          if (b.right > window.innerWidth + 1 && b.width > 4)
            tran.push(`${el.tagName.toLowerCase()}.${(el.className || '').toString().slice(0, 40)} right=${Math.round(b.right)}`);
          if (tran.length > 6) break;
        }
      }
      return {
        khungNhin: window.innerWidth,
        taiLieu: document.documentElement.scrollWidth,
        trang: r(pg), vo: r(shell), noiDung: r(main),
        tranNgang: document.documentElement.scrollWidth > window.innerWidth + 1,
        thuPhamTran: tran,
      };
    });
    bao.push({ khung: nhan, trang: ten, duong, ...d });
    await page.screenshot({ path: join(out, nhan, `${ten}.png`), fullPage: true });
  }
}

writeFileSync(join(out, 'do_dac.json'),
  JSON.stringify({ base: BASE, luc: new Date().toISOString(), do: bao, loiConsole: loi, mangLoi: mang }, null, 2));

console.log('== BE RONG @1920 ==');
for (const r of bao.filter(x => x.khung === '1920'))
  console.log(`  ${r.trang.padEnd(14)} trang=${r.trang_ ?? r.trang}px noiDung=${r.noiDung}px  tran=${r.tranNgang}`);
console.log(`\nloi console: ${loi.length}`);
loi.slice(0, 15).forEach(l => console.log('  ' + l));
console.log(`phan hoi >=400: ${mang.length}`);
mang.slice(0, 15).forEach(l => console.log('  ' + l));
const tran = bao.filter(x => x.tranNgang);
console.log(`\ntran ngang: ${tran.length} truong hop`);
tran.forEach(t => console.log(`  ${t.khung} ${t.trang}: tai lieu ${t.taiLieu} > khung ${t.khungNhin} :: ${t.thuPhamTran.join(' | ')}`));

await browser.close();
