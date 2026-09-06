/*
 * mobile_quet.js — mot luot quet mobile tren moi route khach hang.
 *
 * ⛔ Khong chay truc tiep. `tools/mobile_qa.py quet` thay dong `CAU_HINH` ben
 *    duoi bang cau hinh that roi goi:
 *
 *      playwright-cli -s=<phien> --raw run-code --filename=<tep tam>
 *
 *    Phai thay-roi-goi chu khong truyen bien moi truong: `run-code` chay trong
 *    ngu canh trang, khong co `process`. (Do 05/09: `process is not defined`.)
 *
 * ## Bon bai hoc da nam san trong bo do nay — dung go chung ra
 *
 * 1. `getBoundingClientRect().right` bao ca phan da bi mot to tien
 *    `overflow-x:auto` HAP THU. Khong loc theo to tien cuon thi bo do chi nham
 *    thu pham — da xay ra ba lan trong mot phien.
 *
 * 2. Co chu o nhap phai doc `getComputedStyle`: luat 16px nam trong
 *    `@media(pointer:coarse)`, thuoc tinh HTML khong thay no.
 *
 * 3. Vung cham TRONG mot canvas bi thu phong phai chia lai cho zoom truoc khi
 *    so voi 44px — neu khong ta "sua" mot thu chi nho vi nguoi dung dang thu
 *    nho canvas.
 *
 * 4. `target_be` la danh sach UNG VIEN, khong phai danh sach loi: WCAG 2.5.8
 *    mien tru lien ket van ban trong dong. Bao cao no nhu so loi la bao cao sai.
 */
async (page) => {
  const CAU_HINH = {"goc":"http://127.0.0.1:8123","cookie":"","routes":["/"],"khung":["p390"]};

  const KHUNG = {
    // 195px = mot may 390px o muc phong to 200% (WCAG 1.4.10 doi 320px;
    // 195 la chat hon tieu chuan, ghi ro o docs/MOBILE/07_BE_MAT_CHUAN.md).
    p195: { w: 195, h: 844, cham: true },
    p320: { w: 320, h: 720, cham: true },
    p390: { w: 390, h: 844, cham: true },
    p430: { w: 430, h: 932, cham: true },
    tab768: { w: 768, h: 1024, cham: true },
    land844: { w: 844, h: 390, cham: true },
    desk1440: { w: 1440, h: 900, cham: false },
  };

  const DO = () => {
    const de = document.documentElement;
    const vw = de.clientWidth;
    const r = { tran_ngang: Math.round(de.scrollWidth - vw) };

    // (1) chi tinh la tran khi KHONG co to tien tu cuon hap thu
    //
    // 🔴 BAN DAU CUA HAM NAY SAI VOI PHAN TU DINH VI TUYET DOI, va do la ly do
    //    thu pham o 195px "khong khoanh duoc" suot phien 05-06/09.
    //
    //    `overflow-x` cua mot to tien CHI cat duoc mot phan tu `position:absolute`
    //    khi to tien ay la KHOI CHUA cua no — tuc la to tien DA DINH VI gan nhat.
    //    Mot to tien `static` co `overflow-x:auto` nam giua thi KHONG cat gi ca.
    //
    //    Do duoc luc ay: `header.hdr` co scrollWidth 250 / clientWidth 195, ma
    //    bon con TRUC TIEP cua no ket thuc o x=185 (vua). Phan doi ra den tu mot
    //    hau due tuyet doi — va ham cu LOAI no ra khoi danh sach nghi can.
    //
    // ⛔ `position:fixed` thi khong to tien nao hap thu duoc (tru khi co
    //    `transform`/`filter`/`contain` tao khoi chua moi — hiem, va neu co thi
    //    ta bao THUA mot ung vien, re hon bo sot thu pham).
    const coToTienCuon = (el) => {
      const viTri = getComputedStyle(el).position;
      if (viTri === 'fixed') return false;
      const tuyetDoi = viTri === 'absolute';
      let a = el.parentElement;
      let daQuaKhoiChua = !tuyetDoi;   // phan tu thuong: moi to tien deu cat duoc
      while (a && a !== de) {
        const cs = getComputedStyle(a);
        const cuon = ['auto', 'scroll', 'hidden'].includes(cs.overflowX);
        if (!daQuaKhoiChua && cs.position !== 'static') daQuaKhoiChua = true;
        if (daQuaKhoiChua && cuon) return true;
        a = a.parentElement;
      }
      return false;
    };
    if (r.tran_ngang > 1) {
      const thu = [];
      for (const el of document.querySelectorAll('body *')) {
        const b = el.getBoundingClientRect();
        if (b.width === 0 || b.height === 0 || b.right <= vw + 1) continue;
        if (coToTienCuon(el)) continue;
        thu.push({ t: el.tagName.toLowerCase(),
          c: (typeof el.className === 'string' ? el.className : '').slice(0, 40),
          p: getComputedStyle(el).position,
          r: Math.round(b.right) });
      }
      thu.sort((a, b) => b.r - a.r);
      r.tran_mau = thu.slice(0, 3);
    }

    // (2) co chu o nhap — computed, khong phai thuoc tinh
    const nho = [];
    let hien = 0;
    for (const el of document.querySelectorAll('input,textarea,select')) {
      const t = (el.getAttribute('type') || '').toLowerCase();
      if (['hidden', 'checkbox', 'radio', 'file', 'color', 'range'].includes(t)) continue;
      const b = el.getBoundingClientRect();
      if (b.width === 0 && b.height === 0) continue;
      hien++;
      const f = parseFloat(getComputedStyle(el).fontSize);
      if (f < 16) nho.push({ t: el.tagName.toLowerCase() + (t ? ':' + t : ''), f,
        n: (el.id || el.name || '').slice(0, 20) });
    }
    r.input_hien = hien;
    r.input_nho = nho.length;
    if (nho.length) r.input_nho_mau = nho.slice(0, 3);

    // (3) vung cham — chia lai cho zoom neu nam trong mot canvas React Flow
    const vpFlow = document.querySelector('.react-flow__viewport');
    let zoom = 1;
    if (vpFlow) {
      try { zoom = new DOMMatrix(getComputedStyle(vpFlow).transform).a || 1; } catch (e) { zoom = 1; }
    }
    const be = [];
    for (const el of document.querySelectorAll('a,button,summary,[role=button]')) {
      const b = el.getBoundingClientRect();
      if (b.width === 0 || b.height === 0) continue;
      if (b.top > innerHeight * 3) continue;
      const trongFlow = vpFlow ? vpFlow.contains(el) : false;
      const cao = trongFlow ? b.height / zoom : b.height;
      if (cao < 44) {
        be.push({ t: el.tagName.toLowerCase(),
          c: (typeof el.className === 'string' ? el.className : '').slice(0, 30),
          h: Math.round(cao), zoom: trongFlow ? +zoom.toFixed(2) : 1,
          x: (el.textContent || '').trim().slice(0, 16) });
      }
    }
    r.target_be = be.length;
    if (be.length) r.target_be_mau = be.slice(0, 3);

    // (4) media
    const vids = [...document.querySelectorAll('video')];
    r.video = vids.length;
    r.video_thieu_psi = vids.filter((v) => !v.hasAttribute('playsinline')).length;
    r.audio = document.querySelectorAll('audio').length;

    // (5) viewport + thanh dinh day
    const mv = document.querySelector('meta[name=viewport]');
    r.meta_vp = mv ? mv.getAttribute('content') : null;
    const day = [];
    for (const el of document.querySelectorAll('body *')) {
      const cs = getComputedStyle(el);
      if (cs.position !== 'fixed' && cs.position !== 'sticky') continue;
      const b = el.getBoundingClientRect();
      if (b.height === 0) continue;
      if (b.bottom >= innerHeight - 4 && b.top > innerHeight / 2) {
        day.push({ c: (typeof el.className === 'string' ? el.className : '').slice(0, 30),
          pb: cs.paddingBottom });
      }
    }
    if (day.length) r.dinh_day = day.slice(0, 2);

    // (6) bang: co bi giau cot hay tran ma khong cuon duoc khong
    // ⚠️ Bang co the tu cuon TRONG CHINH NO, khong can mot to tien cuon.
    //
    // 🔴 Do 06/09: sau khi `.table` duoc cho `display:block;overflow-x:auto` o
    //    duoi 320px, bo do nay bao "6 bang tran ma khong cuon duoc" trong khi
    //    ca sau deu cuon duoc — vi no chi hoi TO TIEN. Mot bao dong gia o dung
    //    cho vua sua xong la cach nhanh nhat de nguoi ta thoi doc bo do.
    const tuCuon = (el) => ['auto', 'scroll'].includes(getComputedStyle(el).overflowX);
    r.bang_tran = [...document.querySelectorAll('table')].filter((t) => {
      const b = t.getBoundingClientRect();
      return t.scrollWidth > Math.round(b.width) + 1
        && !tuCuon(t) && !coToTienCuon(t);
    }).length;
    r.cot_an = [...document.querySelectorAll('th,td')].filter(
      (e) => getComputedStyle(e).display === 'none').length;

    return r;
  };

  const browser = page.context().browser();
  const ket = {};
  for (const ten of CAU_HINH.khung) {
    const k = KHUNG[ten];
    if (!k) continue;
    const ctx = await browser.newContext({
      viewport: { width: k.w, height: k.h },
      isMobile: k.cham, hasTouch: k.cham,
      deviceScaleFactor: k.cham ? 3 : 1, locale: 'vi-VN',
    });
    if (CAU_HINH.cookie) {
      const i = CAU_HINH.cookie.indexOf('=');
      await ctx.addCookies([{ name: CAU_HINH.cookie.slice(0, i),
        value: CAU_HINH.cookie.slice(i + 1),
        // ⚠️ `URL` khong ton tai trong ngu canh `run-code`. Tach ten may
        //    bang chuoi — mot dong, va no khong phu thuoc vao thu gi ca.
        domain: CAU_HINH.goc.replace(/^https?:\/\//, '').split(/[:/]/)[0],
        path: '/' }]);
    }
    const p = await ctx.newPage();
    const loi = [];
    p.on('console', (m) => { if (m.type() === 'error') loi.push(m.text().slice(0, 120)); });
    p.on('pageerror', (e) => loi.push('PAGEERROR ' + String(e).slice(0, 120)));

    for (const route of CAU_HINH.routes) {
      loi.length = 0;
      let st = 0;
      try {
        const resp = await p.goto(CAU_HINH.goc + route, { waitUntil: 'networkidle', timeout: 30000 });
        st = resp ? resp.status() : 0;
      } catch (e) { st = -1; }
      await p.waitForTimeout(400);
      let m = {};
      try { m = await p.evaluate(DO); } catch (e) { m = { loi_do: String(e).slice(0, 100) }; }
      m.status = st;
      m.console_loi = loi.length;
      if (loi.length) m.console_mau = loi.slice(0, 2);
      ket[ten + ' ' + route] = m;
    }
    await ctx.close();
  }
  return JSON.stringify(ket);
}
