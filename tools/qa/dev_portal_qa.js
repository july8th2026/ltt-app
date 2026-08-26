// Soi khu /developers bang trinh duyet that.
//
// Chup anh + do BA thu ma mot anh chup khong noi duoc: be rong that su duoc
// dung, o nhap nao dang hien tho, va tran ngang cua tai lieu.
//
//   playwright-cli -s=devui open "http://127.0.0.1:8101/?qa=before"
//   playwright-cli -s=devui --raw run-code --filename=tools/qa/dev_portal_qa.js
//
// ⚠️ `run-code` nap tep nay nhu MOT BIEU THUC HAM — khong require, khong import,
//    khong `process`, khong ghi tep (tru `page.screenshot({path})`, Playwright
//    tu tao thu muc). Ket qua tra ve duoi dang JSON de ben goi ghi ra tep.
//
// ⭐ Dich va thu muc ra LAY TU DIA CHI DANG MO — vi do la thu duy nhat ben goi
//    truyen vao duoc. Goc trang = dich; `?qa=<nhan>` = ten thu muc anh.
async page => {
  // Boi tay chu khong `new URL`: boi canh cua `run-code` khong co URL, khong
  // co process, khong co require. Dung mot bieu thuc, dung mot lan.
  const mo = page.url();
  const BASE = (mo.match(/^https?:\/\/[^/?#]+/) || ['http://127.0.0.1:8101'])[0];
  const nhanRa = ((mo.match(/[?&]qa=([^&#]*)/) || [])[1] || 'before')
    .replace(/[^a-z0-9_-]/gi, '');
  const OUT = 'docs/developer_portal_mvp_ui/evidence/' + (nhanRa || 'before');
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
  page.on('console', m => { if (m.type() === 'error') loi.push(page.url() + ' :: ' + m.text()); });
  page.on('pageerror', e => loi.push(page.url() + ' :: PAGEERROR ' + e.message));
  page.on('response', r => { if (r.status() >= 400) mang.push(r.status() + ' ' + r.url()); });

  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto(BASE + '/login', { waitUntil: 'networkidle' });
  await page.fill('input[name=username]', EMAIL);
  await page.fill('input[name=password]', PASS);
  await page.click('button[type=submit]');
  await page.waitForLoadState('networkidle');
  if (page.url().includes('/login')) throw new Error('DANG NHAP THAT BAI: ' + page.url());

  for (const [nhan, w, h] of KHUNG) {
    await page.setViewportSize({ width: w, height: h });
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
              tran.push(el.tagName.toLowerCase() + '.' + String(el.className || '').slice(0, 36) + '@' + Math.round(b.right));
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
          // O nhap KHONG khop luat CSS nao cua ta thi trinh duyet ve no: nen
          // sang tren mot trang toi. Do bang mau tinh duoc, khong bang mat.
          oTho: [...document.querySelectorAll('.app-main input, .app-main select, .app-main textarea')]
            .filter(el => {
              if ((el.getAttribute('type') || '').toLowerCase() === 'hidden') return false;
              const m = getComputedStyle(el).backgroundColor.match(/\d+/g);
              return m && (+m[0] + +m[1] + +m[2]) / 3 > 120;
            })
            .map(el => el.tagName.toLowerCase() + '[' + (el.getAttribute('type') || 'no-type') + ']#' + (el.id || '?')),
          fieldsetTho: [...document.querySelectorAll('.app-main fieldset')]
            .filter(el => getComputedStyle(el).borderTopStyle === 'groove').length,
        };
      });
      bao.push(Object.assign({ khung: nhan, trang: ten, duong }, d));
      await page.screenshot({ path: OUT + '/' + nhan + '/' + ten + '.png', fullPage: true });
    }
  }
  return JSON.stringify({ base: BASE, luc: new Date().toISOString(),
                          do: bao, loiConsole: loi, mangLoi: mang });
}
