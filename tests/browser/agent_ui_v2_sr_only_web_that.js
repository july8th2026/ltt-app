// Lam ro MOT cau hoi: `.sr-only` co that su an `FlowStatus` tren WEB THAT?
//
// ## Vi sao can phep do NAY
//
// Lan UI-7 bao (28/09): *"`.sr-only` khong duoc dinh nghia o dau trong
// `canvas.css` ⇒ dong 'N node · M ket noi trong renderer' DANG HIEN cho nguoi
// dung that"*. Nua dau DUNG — `canvas.css` khong dinh nghia no. Nua sau la mot
// KET LUAN, va no duoc rut ra tu mot hop thu `vite dev` (cong 8202) chi nap
// bundle cua `agent-canvas`.
//
// Trang THAT nap HAI bang: `base.html` nap `/static/ltt.css` (co `.sr-only` o
// dong 130) roi `agent_canvas.html` moi nap `canvas_css`. Va chinh
// `agent_canvas.html` dung `<h1 class="sr-only">` cho tieu de cua no.
//
// ⇒ Cau hoi that khong phai *"canvas.css co dinh nghia .sr-only khong"* ma
//   *"tren trang that, phan tu ay co hien ra voi nguoi sang mat khong"*. Hai cau
//   hoi khac nhau, va hop thu cua UI-7 chi tra loi duoc cau thu nhat.
//
// ## ⛔ `getComputedStyle` mot minh khong du
//
// Mot `position:absolute; clip:rect(0,0,0,0)` VAN co `display:block` va
// `visibility:visible`. Nen phep do phai la HINH HOC: o vuong bao quanh phai
// gan nhu bang khong, va `elementFromPoint` o giua man hinh phai KHONG tra ve
// no. Do la cung bai hoc voi `.node-cong` 28/09: toa do dung ⛔ khong co nghia
// la nhin thay duoc.
//
//     python tools\chay_web_that.py tests\browser\agent_ui_v2_sr_only_web_that.js --phien sronly
async page => {
  const COOKIE = '__LTT_COOKIE__';
  if (!COOKIE || COOKIE.startsWith('__LTT_'))
    throw new Error('chua dien cookie — chay qua `python tools/chay_web_that.py`');

  const loi = [];
  page.on('pageerror', e => loi.push('pageerror: ' + e.message));

  // ⚠️ `__LTT_COOKIE__` duoc thay bang GIA TRI, khong phai `session=<gia tri>`
  //    (`chay_web_that.py` bo tien to truoc khi dien). Lan dau toi `split('=')`
  //    o day va nhan `value: undefined` — Playwright bao loi kieu chu khong bao
  //    loi dang nhap, nen no de bi doc thanh "trang khong nap duoc".
  await page.context().addCookies([{
    name: 'session', value: COOKIE, domain: 'app.lttstudios.com', path: '/',
    httpOnly: true, secure: true,
  }]);
  await page.setViewportSize({ width: 1440, height: 900 });

  await page.goto('https://app.lttstudios.com/agent/canvas',
                  { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForSelector('[data-testid="flow-store-status"]', { timeout: 45000 });

  const do_duoc = await page.evaluate(() => {
    const e = document.querySelector('[data-testid="flow-store-status"]');
    const o = e.getBoundingClientRect();
    const cs = getComputedStyle(e);
    // Bang nao dinh nghia `.sr-only`? Doc tu chinh CSSOM cua trang, khong doan
    // tu ten tep trong kho.
    const nguon = [];
    for (const sheet of document.styleSheets) {
      let luat;
      try { luat = sheet.cssRules } catch { continue }  // bang khac goc
      for (const r of luat)
        if (r.selectorText && r.selectorText.split(',').some(
            s => s.trim() === '.sr-only'))
          nguon.push((sheet.href || 'inline').split('?')[0]);
    }
    return {
      chu: (e.textContent || '').trim().slice(0, 60),
      o: { w: Math.round(o.width), h: Math.round(o.height) },
      position: cs.position, clip: cs.clip, overflow: cs.overflow,
      // Phep do THAT: giua o vuong cua no, trinh duyet tra ve phan tu nao?
      o_tam: (() => {
        const t = document.elementFromPoint(o.left + o.width / 2,
                                            o.top + o.height / 2);
        return t === e ? 'CHINH NO' : (t ? t.className || t.tagName : 'khong co');
      })(),
      nguon_sr_only: nguon,
      // Doi chung: tieu de cua chinh template cung dung `.sr-only`. Neu lop nay
      // chet thi CA HAI phai hien — mot trong hai hien mot minh la vo ly.
      h1: (() => {
        const h = document.querySelector('h1.sr-only');
        if (!h) return 'khong co h1.sr-only';
        const r = h.getBoundingClientRect();
        return `${Math.round(r.width)}x${Math.round(r.height)}`;
      })(),
    };
  });

  // ⚠️ Ket qua tra ve bang `return`, ⛔ KHONG bang `console.log`: playwright-cli
  //    in GIA TRI TRA VE, con `console.log` trong ham nay bien mat. Lan dau toi
  //    dung `console.log` va nhan mot luot chay "khong in gi" — trong y het mot
  //    kich ban chet, trong khi no da chay xong.
  const an = do_duoc.o.w <= 1 && do_duoc.o.h <= 1;
  return {
    status: (an && !loi.length) ? 'PASS' : 'FAIL',
    KET_LUAN: an ? 'DA AN (UI-7 bao dong canh bao)' : 'DANG HIEN (UI-7 bao dung)',
    ...do_duoc, loi,
  };
}
