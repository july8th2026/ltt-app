/*
 * a11y_quet.js — chay `axe-core` tren moi route, mot lan mot khung.
 *
 * ⛔ Khong chay truc tiep. `tools/check_a11y.py` thay dong `CAU_HINH` ben duoi
 *    bang cau hinh that roi goi:
 *
 *      playwright-cli -s=<phien> --raw run-code --filename=<tep tam>
 *
 *    Cung khuon voi `mobile_quet.js` — xem docstring o do ve vi sao phai
 *    THAY-ROI-GOI chu khong truyen bien moi truong.
 *
 * ## Ba dieu da phai doc truoc khi viet, dung go ra
 *
 * 1. `page.addScriptTag` KHONG dung duoc o day. No chen mot the <script> noi
 *    tuyen, ma app dat CSP `script-src 'nonce-...'` — trinh duyet chan, va
 *    trieu chung la `axe is not defined` chu khong phai mot loi CSP de doc.
 *    `page.evaluate(<ma nguon>)` chay qua CDP nen KHONG bi CSP chan.
 *
 * 2. `axe.run()` tra ca `violations` lan `incomplete`. `incomplete` la
 *    "axe khong tu ket luan duoc, can nguoi xem" — dem no nhu loi la bao cao
 *    sai, dung kieu `target_be` trong `mobile_quet.js`. Giu rieng hai cot.
 *
 * 3. Mot route bi day ve `/login` cho ra bao cao DEP cua trang login, khong
 *    phai cua route ay. `mobile_qa` da tra gia mot lan vi khong kiem dieu nay
 *    (05/09), nen o day kiem `url_thuc` va gan co `CHUA_DANG_NHAP`.
 */
async (page) => {
  const CAU_HINH = {"goc":"http://127.0.0.1:8100","cookie":"","routes":["/"],"khung":["p390"],"axe":""};

  const KHUNG = { p390: { width: 390, height: 844 },
                  p195: { width: 195, height: 844 },
                  m768: { width: 768, height: 1024 },
                  d1280: { width: 1280, height: 900 } };

  const ket = {};

  if (CAU_HINH.cookie) {
    const [ten, ...phan] = CAU_HINH.cookie.split('=');
    const u = new URL(CAU_HINH.goc);
    await page.context().addCookies([{
      name: ten.trim(), value: phan.join('=').trim(),
      domain: u.hostname, path: '/'
    }]);
  }

  for (const ten_khung of CAU_HINH.khung) {
    const kt = KHUNG[ten_khung] || KHUNG.p390;
    await page.setViewportSize(kt);

    for (const route of CAU_HINH.routes) {
      const khoa = ten_khung + ' ' + route;
      const m = {};
      try {
        await page.goto(CAU_HINH.goc + route, { waitUntil: 'domcontentloaded', timeout: 30000 });
        await page.waitForTimeout(400);

        m.url_thuc = page.url().replace(CAU_HINH.goc, '');

        // ⚠️ App them TIEN TO NGON NGU: `/bang-gia` -> `/en/bang-gia`. Nen
        //    "url doi" KHONG dong nghia voi "bi day ve login" — ban dau toi so
        //    tho `url_thuc !== route` va no bao nham `/login` -> `/en/login`
        //    la CHUA DANG NHAP, roi bo qua ca mot route co that.
        //
        // ⇒ Chi la bi day ve login khi DICH la login MA NGUON thi khong.
        const bo_ngon_ngu = (u) => u.replace(/^\/[a-z]{2}(?=\/|$)/, '') || '/';
        const dich = bo_ngon_ngu(m.url_thuc.split('?')[0]);
        const nguon = bo_ngon_ngu(route);
        if (dich !== nguon && /\/login$/.test(dich) && !/\/login$/.test(nguon)) {
          // Bao cao cua trang login, khong phai cua route nay.
          m.CHUA_DANG_NHAP = true;
          ket[khoa] = m;
          continue;
        }

        // (1) Nap axe qua CDP — KHONG qua the <script>, xem ghi chu 1.
        await page.evaluate(CAU_HINH.axe);

        // (2) Chay. `resultTypes` gioi han thu axe phai dung nut de bao cao,
        //     nen bao cao nho di nhieu ma van du de dem theo LUAT.
        const kq = await page.evaluate(async () => {
          const r = await window.axe.run(document, {
            resultTypes: ['violations', 'incomplete'],
            reporter: 'v2',
          });
          const gom = (ds) => ds.map((v) => ({
            id: v.id,
            impact: v.impact || 'unknown',
            so: (v.nodes || []).length,
            mau: (v.nodes || []).slice(0, 2).map((n) => (n.target || []).join(' ')),
          }));
          return { vi_pham: gom(r.violations), chua_ro: gom(r.incomplete) };
        });

        m.vi_pham = kq.vi_pham;
        m.chua_ro = kq.chua_ro;
        m.so_vi_pham = kq.vi_pham.reduce((a, b) => a + b.so, 0);
        m.so_luat = kq.vi_pham.length;

        // (3) `prefers-reduced-motion` — `axe` KHONG do cai nay.
        //
        // ⭐ Do 07/09 tren `/`: 26 transition > 50ms o che do `no-preference`,
        //    va **0** o che do `reduce`. Tuc luat trong `ltt.css` co hieu luc
        //    that. Nhung khong co gi chot dieu do, nen no troi duoc bat cu luc
        //    nao — do la ly do phep do nay nam o day.
        //
        // ⛔ Doc CA HAI che do. Chi doc `reduce` roi thay 0 thi khong phan biet
        //    duoc "luat co hieu luc" voi "trang nay von khong co chuyen dong
        //    nao" — mot so 0 khong doi chung khong phai mot phat hien.
        const dem_dong = async () => page.evaluate(() => {
          let anim = 0, vo_han = 0, chuyen = 0;
          for (const el of document.querySelectorAll('*')) {
            const s = getComputedStyle(el);
            if ((parseFloat(s.animationDuration) || 0) > 0.05) anim++;
            if (s.animationIterationCount === 'infinite') vo_han++;
            if ((parseFloat(s.transitionDuration) || 0) > 0.05) chuyen++;
          }
          return { anim, vo_han, chuyen };
        });
        await page.emulateMedia({ reducedMotion: 'no-preference' });
        await page.waitForTimeout(120);
        m.rm_thuong = await dem_dong();
        await page.emulateMedia({ reducedMotion: 'reduce' });
        await page.waitForTimeout(120);
        m.rm_giam = await dem_dong();
        await page.emulateMedia({ reducedMotion: 'no-preference' });
      } catch (e) {
        m.LOI = String(e).slice(0, 200);
      }
      ket[khoa] = m;
    }
  }
  return JSON.stringify(ket);
}
