// Nghiem thu TRINH DUYET cho luu tru workflow (dieu phoi, 28/09/2026).
//
// ## Vi sao can kich ban nay khi da co test_5603 + test_5604
//
// `test_5603` chung minh CUA HTTP dat/xoa duoc `archived_at`.
// `test_5604` chung minh TANG TRANG ve dung nut trong dung khung nhin.
// Ca hai doc HTML bang chuoi. ⛔ Khong bai nao chung minh **mot cu BAM that su
// lam workflow bien mat** — vi giua HTML va hanh vi con mot lop JS:
// `goi()` + `window.location.reload()`.
//
// 🔴 Va do dung la cho de vo im lang. Bang bo chon la mot bang TAY:
//
//     { chon: '[data-wfl-luu-tru]', khoa: 'wflLuuTru', cua: 'luu-tru' }
//
// Neu `khoa` lech mot chu (`wflLuutru`), `nut.dataset[khoa]` la `undefined`,
// URL thanh `/workflows/undefined/luu-tru`, may chu tra 404 — va bai kiem doc
// HTML van XANH vi thuoc tinh **co mat** dung cho. Ban dau toi da viet dung
// mot bang sai nhu vay (`cua.replace('-','-')`, mot no-op vo nghia).
//
// ⇒ Phep do o day phai la: BAM -> dem lai so dong -> va doc lai tu MAY CHU.
//
//     python tools\chay_may_chu_thu.py 8196   (hoac uvicorn, xem docstring)
//     playwright-cli -s=luutru run-code --filename=tests/browser/agent_ui_v2_luu_tru_nghiem_thu.js
async page => {
  // ⚠️ Hang so phai nam TRONG ham: playwright-cli `run-code` danh gia tep nay
  //    nhu MOT bieu thuc, nen mot `const` o muc ngoai cung nem
  //    `SyntaxError: Unexpected token 'const'` — mot loi CU PHAP, trong y het
  //    kich ban sai logic.
  const GOC = 'http://127.0.0.1:8196';
  const EMAIL = 'agent-ui0@example.com';
  const MAT_KHAU = 'Browser-ui0-2026';
  const loi = [], loiTrang = [], req5xx = [];
  try {
  page.on('pageerror', e => loiTrang.push(e.message));
  page.on('console', m => { if (m.type() === 'error') loiTrang.push('console: ' + m.text()); });
  page.on('response', r => { if (r.status() >= 500) req5xx.push(`${r.status()} ${r.url()}`); });
  const check = (dk, msg) => { if (!dk) loi.push(msg); };
  // ⭐ `chan()` = mot check MA CAC BUOC SAU PHU THUOC VAO.
  //
  // 🔴 Vi sao can no: tiem loi "khoa dataset lech mot chu" lam phep do 1 do dung
  //    nhu thiet ke — nhung roi kich ban chay tiep, va no chet o
  //    `locator('[data-wfl-mo-lai]').click()` voi mot `TimeoutError`. Bao cao
  //    khi ay chi vao buoc **Mo lai**, trong khi thu hong la buoc **Luu tru**,
  //    va `loi` da thu san cau dung thi khong bao gio duoc tra ve.
  //    ⇒ Mot phep do dung, mot ket qua do dung, BAO CAO gan so cho SAI BUOC —
  //      y het ca `503` cua `/login` sang nay. Lan nay no o trong chinh bo do
  //      cua toi.
  const chan = (dk, msg) => {
    if (!dk) { loi.push(msg); throw { __dung_som: true, loi, so } }
  };
  const so = {};

  // ── Dang nhap ─────────────────────────────────────────────────────────────
  await page.goto(`${GOC}/login`, { waitUntil: 'load' });
  // ⚠️ Ho so Playwright GIU cookie giua cac luot chay, nen `/login` co the da
  //    chuyen huong di. Dang nhap CO DIEU KIEN — mot `page.fill` vo dieu kien o
  //    day nem `TimeoutError: waiting for input[name="username"]`, nghe y het
  //    "trang khong nap duoc" trong khi that ra da dang nhap san.
  const canDangNhap = await page.locator('input[name="username"]').count();
  if (!canDangNhap) {
    await page.goto(`${GOC}/agent/workflows`, { waitUntil: 'load' });
    so.daDangNhapSan = true;
  }
  if (canDangNhap) {
  await page.fill('input[name="username"]', EMAIL);
  await page.fill('input[name="password"]', MAT_KHAU);
  // ⚠️ `click` + `waitForLoadState` KHONG du: form login tra 303, va mot `goto`
  //    phat ngay sau do bi cat bang `net::ERR_ABORTED` (dieu huong dang do bi
  //    mot dieu huong khac chen). Cho DUNG lan dieu huong cua form.
  await Promise.all([
    page.waitForNavigation({ waitUntil: 'load', timeout: 30000 }),
    page.click('button[type="submit"], input[type="submit"]'),
  ]);
  }
  const dn = async (duong) => {
    for (let i = 0; i < 3; i++) {
      try { return await page.goto(duong, { waitUntil: 'load', timeout: 30000 }) }
      catch (e) { if (i === 2) throw e; await page.waitForTimeout(500) }
    }
  };

  const demDong = async () =>
    page.locator('#wfl-ds > li.wfl-o').count();

  // ── Dung san hai workflow qua CUA DA CO (khong bam nut Tao nhieu lan) ─────
  const csrf = await page.evaluate(async () => {
    const r = await fetch('/agent/canvas', { credentials: 'same-origin' });
    const t = await r.text();
    return (t.match(/data-csrf-token="([^"]+)"/) || [])[1] || '';
  });
  check(!!csrf, 'khong lay duoc csrf tu /agent/canvas');

  await page.evaluate(async (tok) => {
    for (const ten of ['browser giu lai', 'browser dem cat di'])
      await fetch('/agent/api/v3/workflows', {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': tok },
        body: JSON.stringify({ name: ten, csrf_token: tok }),
      });
  }, csrf);

  await dn(`${GOC}/agent/workflows`);
  so.truoc = await demDong();
  check(so.truoc >= 2, `can >= 2 workflow de do, co ${so.truoc}`);

  // ⛔ Khong co nut "Kho luu tru" khi kho RONG — do TRUOC khi luu tru.
  so.loiVaoKhoLucRong = await page.locator('a[href*="luu_tru=1"]').count();
  check(so.loiVaoKhoLucRong === 0,
    'kho dang rong ma trang chinh da ve loi vao kho');

  // ── PHEP DO 1: bam "Luu tru" -> dong BIEN MAT ────────────────────────────
  const nut = page.locator('[data-wfl-luu-tru]').first();
  so.idSapCat = await nut.getAttribute('data-wfl-luu-tru');
  await nut.click();
  // Trang tu `location.reload()` sau khi cua tra 200.
  await page.waitForFunction(
    (n) => document.querySelectorAll('#wfl-ds > li.wfl-o').length === n - 1,
    so.truoc, { timeout: 15000 }).catch(() => {});
  so.sau = await demDong();
  chan(so.sau === so.truoc - 1,
    `bam Luu tru: ${so.truoc} dong -> ${so.sau}, cho doi ${so.truoc - 1}`);
  so.conThayIdDaCat = await page.locator(
    `#wfl-ds > li[data-wf-id="${so.idSapCat}"]`).count();
  check(so.conThayIdDaCat === 0, 'workflow da luu tru van con tren danh sach');

  // ⭐ Doc lai tu MAY CHU: giao dien co the xoa dong ma khong ghi gi.
  so.mocTrenMayChu = await page.evaluate(async (id) => {
    const r = await fetch('/agent/api/v3/workflows?luu_tru=1',
                          { credentials: 'same-origin' });
    const j = await r.json();
    const o = (j.items || []).find(w => w.id === id);
    return o ? o.da_luu_tru : null;
  }, so.idSapCat);
  check(so.mocTrenMayChu === true,
    `may chu khong ghi da_luu_tru cho ${so.idSapCat}: ${so.mocTrenMayChu}`);

  // ── PHEP DO 2: loi vao kho hien ra, va no noi SO LUONG ───────────────────
  const loiVao = page.locator('a[href*="luu_tru=1"]');
  so.loiVaoKho = await loiVao.count();
  chan(so.loiVaoKho === 1, `loi vao kho: ${so.loiVaoKho} cai, cho doi 1`);
  if (so.loiVaoKho) {
    so.nhanLoiVao = (await loiVao.first().textContent() || '').trim();
    check(/\(1\)/.test(so.nhanLoiVao),
      `loi vao kho khong noi so luong: ${JSON.stringify(so.nhanLoiVao)}`);
    await loiVao.first().click();
    await page.waitForLoadState('domcontentloaded');
  }

  // ── PHEP DO 3: trong kho — dung nut, dung nhan, co duong ve ─────────────
  so.trongKho = await demDong();
  check(so.trongKho === 1, `kho co ${so.trongKho} dong, cho doi 1`);
  so.nutMoLai = await page.locator('[data-wfl-mo-lai]').count();
  so.nutLuuTruTrongKho = await page.locator('[data-wfl-luu-tru]').count();
  so.nutNhanBanTrongKho = await page.locator('[data-wfl-nhan-ban]').count();
  chan(so.nutMoLai === 1, `kho phai co 1 nut Mo lai, co ${so.nutMoLai}`);
  check(so.nutLuuTruTrongKho === 0, 'kho van hien nut Luu tru');
  check(so.nutNhanBanTrongKho === 0,
    'kho hien Nhan ban — no se sinh mot ban DANG DUNG tu mot trang kho');
  so.duongVe = await page.locator('a[href="/agent/workflows"]').count();
  check(so.duongVe >= 1, 'trong kho ma khong co duong ve');

  // ── PHEP DO 4: bam "Mo lai" -> ve danh sach chinh ────────────────────────
  await page.locator('[data-wfl-mo-lai]').first().click();
  await page.waitForLoadState('domcontentloaded');
  await dn(`${GOC}/agent/workflows`);
  so.sauMoLai = await demDong();
  check(so.sauMoLai === so.truoc,
    `sau Mo lai: ${so.sauMoLai} dong, cho doi ${so.truoc}`);
  so.thayLaiIdDaCat = await page.locator(
    `#wfl-ds > li[data-wf-id="${so.idSapCat}"]`).count();
  check(so.thayLaiIdDaCat === 1, 'mo lai roi ma workflow khong tro lai danh sach');

  // ── Suc khoe trang ──────────────────────────────────────────────────────
  check(loiTrang.length === 0, 'loi trang: ' + JSON.stringify(loiTrang));
  check(req5xx.length === 0, '5xx: ' + JSON.stringify(req5xx));

  return loi.length ? { status: 'FAIL', loi, so } : { status: 'PASS', so };
  } catch (e) {
    if (e && e.__dung_som)
      return { status: 'FAIL', dung_som: true, loi: e.loi, so: e.so };
    return { status: 'FAIL', loi: [...loi, 'nem: ' + (e && e.message || e)], so };
  }
}
