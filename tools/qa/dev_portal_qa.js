// Soi khu /developers bang trinh duyet that (chay qua `playwright-cli run-code`).
//
// Chup anh + do BA thu ma mot anh chup khong noi duoc: be rong that su duoc
// dung, loi console, va tran ngang cua tai lieu.
//
//   playwright-cli -s=devui open
//   playwright-cli -s=devui run-code --filename=tools/qa/dev_portal_qa.js
//
// Doi dich/thu muc bang bien moi truong QA_BASE / QA_OUT.
const fs = require('node:fs');
const path = require('node:path');

module.exports = async page => {
  const BASE = process.env.QA_BASE || 'http://127.0.0.1:8101';
  const OUT = process.env.QA_OUT || 'docs/developer_portal_mvp_ui/evidence/before';
  const EMAIL = 'dev-ui-qa@example.com', PASS = 'a-good-password-12';

  const TRANG = [
    ['overview', '/developers'], ['keys', '/developers/keys'],
    ['projects', '/developers/projects'], ['logs', '/developers/logs'],
    ['jobs', '/developers/jobs'], ['usage', '/developers/usage'],
    ['tools', '/developers/tools'], ['playground', '/developers/playground'],
    ['pricing', '/developers/pricing'], ['quickstart', '/developers/quickstart'],
    ['cli', '/developers/cli'], ['docs', '/developers/docs'],
    ['webhooks', '/developers/webhooks'], ['settings', '/developers/settings'],
    ['privacy', '/developers/privacy'], ['notifications', '/developers/notifications'],
  ];
  const KHUNG = [['1920', 1920, 1080], ['1440', 1440, 900], ['1280', 1280, 800],
                 ['1024', 1024, 768], ['768', 768, 1024], ['390', 390, 844]];
  // O khung trung gian chi chup trang tieu bieu — du de bat vo/bo cuc vo,
  // khong sinh 96 anh phai xem bang mat.
  const CHINH = new Set(['overview', 'keys', 'logs', 'quickstart', 'tools', 'pricing']);

  const loi = [], mang = [], bao = [];
  page.on('console', m => { if (m.type() === 'error') loi.push(`${page.url()} :: ${m.text()}`); });
  page.on('pageerror', e => loi.push(`${page.url()} :: PAGEERROR ${e.message}`));
  page.on('response', r => { if (r.status() >= 400) mang.push(`${r.status()} ${r.url()}`); });

  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' });
  await page.fill('input[name=username]', EMAIL);
  await page.fill('input[name=password]', PASS);
  await page.click('button[type=submit]');
  await page.waitForLoadState('networkidle');
  if (page.url().includes('/login')) throw new Error('DANG NHAP THAT BAI: ' + page.url());

  for (const [nhan, w, h] of KHUNG) {
    await page.setViewportSize({ width: w, height: h });
    fs.mkdirSync(path.join(OUT, nhan), { recursive: true });
    for (const [ten, duong] of TRANG) {
      if (w !== 1920 && w !== 390 && !CHINH.has(ten)) continue;
      await page.goto(BASE + duong, { waitUntil: 'networkidle' });
      const d = await page.evaluate(() => {
        const r = el => el ? Math.round(el.getBoundingClientRect().width) : null;
        const tran = [];
        if (document.documentElement.scrollWidth > window.innerWidth + 1) {
          for (const el of document.querySelectorAll('body *')) {
            const b = el.getBoundingClientRect();
            if (b.right > window.innerWidth + 1 && b.width > 4)
              tran.push(`${el.tagName.toLowerCase()}.${String(el.className || '').slice(0, 36)}@${Math.round(b.right)}`);
            if (tran.length > 6) break;
          }
        }
        return {
          khungNhin: window.innerWidth,
          taiLieu: document.documentElement.scrollWidth,
          trangW: r(document.querySelector('main.page, main[class*=page]')),
          voW: r(document.querySelector('.app-shell')),
          noiDungW: r(document.querySelector('.app-main')),
          tranNgang: document.documentElement.scrollWidth > window.innerWidth + 1,
          thuPham: tran,
          // Bao nhieu o nhap KHONG khop luat CSS nao cua ta -> hien tho.
          oTho: [...document.querySelectorAll('.app-main input, .app-main select, .app-main textarea')]
            .filter(el => {
              const t = (el.getAttribute('type') || '').toLowerCase();
              if (t === 'hidden') return false;
              const bg = getComputedStyle(el).backgroundColor;
              // Nen sang = trinh duyet ve, khong phai ta ve (nen cua ta toi).
              const m = bg.match(/\d+/g);
              return m && (+m[0] + +m[1] + +m[2]) / 3 > 120;
            })
            .map(el => `${el.tagName.toLowerCase()}[${el.getAttribute('type') || 'no-type'}]#${el.id || '?'}`),
          soFieldsetTho: [...document.querySelectorAll('.app-main fieldset')]
            .filter(el => getComputedStyle(el).borderTopStyle === 'groove').length,
        };
      });
      bao.push({ khung: nhan, trang: ten, duong, ...d });
      await page.screenshot({ path: path.join(OUT, nhan, `${ten}.png`), fullPage: true });
    }
  }

  fs.writeFileSync(path.join(OUT, 'do_dac.json'), JSON.stringify(
    { base: BASE, luc: new Date().toISOString(), do: bao, loiConsole: loi, mangLoi: mang }, null, 2));

  const d1920 = bao.filter(x => x.khung === '1920');
  const dong = ['== BE RONG @1920 (khung nhin 1920) =='];
  for (const r of d1920)
    dong.push(`  ${r.trang.padEnd(14)} main.page=${r.trangW}  .app-main=${r.noiDungW}  tran=${r.tranNgang}`);
  const tho = d1920.filter(x => x.oTho.length);
  dong.push('', `== O NHAP HIEN THO (nen sang) ==`);
  tho.forEach(t => dong.push(`  ${t.trang}: ${t.oTho.join(', ')}`));
  const fs2 = d1920.filter(x => x.soFieldsetTho);
  dong.push('', `== FIELDSET VIEN GROOVE MAC DINH ==`);
  fs2.forEach(t => dong.push(`  ${t.trang}: ${t.soFieldsetTho}`));
  const tr = bao.filter(x => x.tranNgang);
  dong.push('', `== TRAN NGANG: ${tr.length} ==`);
  tr.forEach(t => dong.push(`  ${t.khung}/${t.trang}: ${t.taiLieu}>${t.khungNhin} :: ${t.thuPham.join(' | ')}`));
  dong.push('', `loi console: ${loi.length}`, ...loi.slice(0, 12).map(l => '  ' + l));
  dong.push(`phan hoi >=400: ${mang.length}`, ...mang.slice(0, 12).map(l => '  ' + l));
  return dong.join('\n');
};
