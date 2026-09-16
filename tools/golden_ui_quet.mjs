// golden_ui_quet.mjs — quét màn × state × khung nhìn cho chiến dịch Golden UI.
//
//   node tools/golden_ui_quet.mjs --cau-hinh <routes.json> --ra <thu_muc> [--khung 390x844,1440x900]
//
// routes.json: { "goc": "http://127.0.0.1:8140",
//                "cookies": { "khach": "session=...", "admin": "session=..." },
//                "routes": [ { "ten": "nap-pending", "duong": "/nap/don/<id>", "vai": "khach",
//                              "ho": "billing", "cho": 800 } ] }
//
// Mỗi (route, khung) ghi: mã HTTP, ảnh chụp toàn trang, lỗi console, request hỏng,
// tràn ngang, vi phạm axe (theo impact), số h1, lang, landmark main, ô chạm < 24px
// và < 44px (khung hẹp), ô nhập < 16px (khung hẹp).
//
// ⛔ Đây là công cụ ĐO, không phải phán quyết: một route 200 chưa chứng minh gì.
//    Ảnh chụp phải được NGƯỜI xem, và axe chỉ bắt được phần máy bắt được.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const PW = process.env.LTT_PLAYWRIGHT_LIB ||
  'C:/Users/Thang Tuong/AppData/Roaming/npm/node_modules/@playwright/cli/node_modules/playwright';
const AXE = process.env.LTT_AXE_JS ||
  'D:/LTTSTUDIOSAPP/frontend/chatltt/node_modules/axe-core/axe.min.js';
const { chromium } = require(PW);

const arg = (ten, mac) => {
  const i = process.argv.indexOf(ten);
  return i > 0 ? process.argv[i + 1] : mac;
};
const cauHinh = JSON.parse(fs.readFileSync(arg('--cau-hinh'), 'utf8'));
const ra = arg('--ra');
const khung = arg('--khung', '390x844,1440x900').split(',').map(s => {
  const [w, h] = s.split('x').map(Number); return { w, h };
});
const chiLoc = arg('--chi', '');
fs.mkdirSync(ra, { recursive: true });
const axeSrc = fs.readFileSync(AXE, 'utf8');

const browser = await chromium.launch();
const ketQua = [];
const goc = new URL(cauHinh.goc);

for (const r of cauHinh.routes) {
  if (chiLoc && !r.ten.includes(chiLoc)) continue;
  for (const k of khung) {
    const ctx = await browser.newContext({
      viewport: { width: k.w, height: k.h },
      deviceScaleFactor: 1,
      hasTouch: k.w < 768, isMobile: k.w < 768,
      locale: 'vi-VN',
    });
    const ck = r.vai && cauHinh.cookies[r.vai];
    if (ck) {
      const [name, ...rest] = ck.split('=');
      await ctx.addCookies([{ name, value: rest.join('='), domain: goc.hostname, path: '/' }]);
    }
    const page = await ctx.newPage();
    const loi = [], hong = [];
    // Trinh duyet tu ghi ma 4xx/5xx cua CHINH tai lieu vao console — do la hanh vi
    // dung cua mot trang loi, khong phai loi JS. Chi bo dung dong do.
    let maTaiLieu = 0;
    page.on('console', m => { if (m.type() !== 'error') return; const t = m.text();
      if (maTaiLieu >= 400 && t.includes('status of ' + maTaiLieu) && !m.location()?.url?.includes('/static/')) return;
      loi.push(t.slice(0, 300)); });
    page.on('pageerror', e => loi.push('pageerror: ' + e.message.slice(0, 300)));
    page.on('requestfailed', q => hong.push(q.url() + ' ' + (q.failure()?.errorText || '')));
    page.on('response', s => { if (s.status() >= 400 && s.url() !== goc.origin + r.duong) hong.push(s.status() + ' ' + s.url()); });
    const nhan = `${r.ten}@${k.w}`;
    const dong = { ten: r.ten, ho: r.ho, duong: r.duong, vai: r.vai || 'an_danh', khung: `${k.w}x${k.h}` };
    try {
      const resp = await page.goto(cauHinh.goc + r.duong, { waitUntil: 'networkidle', timeout: 45000 });
      dong.http = resp ? resp.status() : null;
      maTaiLieu = dong.http || 0;
      dong.url_cuoi = page.url().replace(cauHinh.goc, '');
      if (r.cho) await page.waitForTimeout(r.cho);
      if (r.bam) { await page.locator(r.bam).first().click().catch(() => {}); await page.waitForTimeout(400); }
      Object.assign(dong, await page.evaluate(() => {
        const de = document.documentElement;
        const rong = de.clientWidth;
        const tran = [];
        for (const el of document.querySelectorAll('body *')) {
          const b = el.getBoundingClientRect();
          if (b.width && b.right > rong + 1 && getComputedStyle(el).position !== 'fixed') {
            tran.push((el.id ? '#' + el.id : el.tagName.toLowerCase()) + '.' + String(el.className || '').split(' ')[0]);
            if (tran.length > 6) break;
          }
        }
        const tuongTac = [...document.querySelectorAll('a[href],button,input:not([type=hidden]),select,textarea,summary,[role=button]')]
          .filter(e => { const b = e.getBoundingClientRect(); return b.width > 0 && b.height > 0 && getComputedStyle(e).visibility !== 'hidden'; });
        const nho24 = tuongTac.filter(e => { const b = e.getBoundingClientRect(); return (b.height < 24 || b.width < 24) && !e.closest('p,li,td') ; }).length;
        const nho44 = tuongTac.filter(e => { const b = e.getBoundingClientRect(); return b.height < 44; }).length;
        const oNhapNho = [...document.querySelectorAll('input:not([type=hidden]):not([type=checkbox]):not([type=radio]),select,textarea')]
          .filter(e => e.getBoundingClientRect().width > 0 && parseFloat(getComputedStyle(e).fontSize) < 16).length;
        const fonts = new Set([...document.querySelectorAll('h1,h2,p,button,.btn,label')].slice(0, 80).map(e => getComputedStyle(e).fontFamily.split(',')[0]));
        return {
          title: document.title,
          lang: de.lang,
          h1: document.querySelectorAll('h1').length,
          h1_text: [...document.querySelectorAll('h1')].map(h => h.textContent.trim().slice(0, 60)),
          main: document.querySelectorAll('main,[role=main]').length,
          tran_ngang: de.scrollWidth > rong + 1, scroll_w: de.scrollWidth, rong,
          tran_phan_tu: tran,
          cham_nho_24: nho24, cham_duoi_44: nho44, o_nhap_duoi_16: oNhapNho,
          inline_style: document.querySelectorAll('[style]').length,
          font: [...fonts],
          chieu_cao: de.scrollHeight,
        };
      }));
      await page.addScriptTag({ content: axeSrc });
      const axe = await page.evaluate(async () => {
        const r = await window.axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'] } });
        return r.violations.map(v => ({ id: v.id, impact: v.impact, n: v.nodes.length, vd: v.nodes[0]?.target?.join(' ') }));
      });
      dong.axe = axe;
      dong.axe_nghiem_trong = axe.filter(v => v.impact === 'critical' || v.impact === 'serious').reduce((s, v) => s + v.n, 0);
      const anh = path.join(ra, nhan.replace(/[^a-z0-9@_-]/gi, '_') + '.png');
      await page.screenshot({ path: anh, fullPage: true, animations: 'disabled' }).catch(async () =>
        page.screenshot({ path: anh, animations: 'disabled' }));
      dong.anh = path.basename(anh);
    } catch (e) {
      dong.loi_quet = String(e.message || e).slice(0, 300);
    }
    dong.console = loi; dong.request_hong = hong.slice(0, 8);
    ketQua.push(dong);
    console.log(`${nhan.padEnd(42)} http=${dong.http} tran=${dong.tran_ngang} axe!=${dong.axe_nghiem_trong} console=${loi.length} hong=${hong.length}${dong.loi_quet ? ' LOI=' + dong.loi_quet : ''}`);
    await ctx.close();
  }
}
await browser.close();
fs.writeFileSync(path.join(ra, 'ket_qua.json'), JSON.stringify(ketQua, null, 2));
console.log('XONG', ketQua.length, 'phep do ->', path.join(ra, 'ket_qua.json'));
