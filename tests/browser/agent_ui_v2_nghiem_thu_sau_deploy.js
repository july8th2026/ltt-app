// Nghiem thu SAU DEPLOY `8907b4dd` tren WEB THAT (che do B).
//
// ## Vi sao kich ban nay khac moi kich ban nghiem thu cua tung lan
//
// Tung lan da chung minh **MA MOI DUNG** (che do A, may chu co lap). Kich ban
// nay hoi mot cau KHAC: **ban DEPLOY co dung khong** — bundle co duoc build lai,
// Cloudflare co phuc vu dung tep, route co that su song tren production.
//
// ⚠️ Neu o day DO ma che do A da XANH ⇒ ⛔ khong phai loi ma, ma la loi DUONG
//    DEPLOY. Kiem theo DUNG thu tu: (1) bundle da build lai chua, (2) `git
//    archive` co mang dung SHA khong, (3) Cloudflare con phuc vu ban cu.
//
// ## Bon thu can do, va chung thuoc ba lan khac nhau
//
//   UI-5   4 cua `/api/v3/ket-noi`     kho ket noi cua khach
//   UI-9   trang `/agent/templates`    mau chay duoc
//   UI-8a  `POST .../nodes/{id}/duyet` cua duyet `core.human`
//   dieu phoi  toc do Canvas           tran gzip vua nang 150k -> 160k
//
// ## ⛔ CHI doc + HEAD, ⛔ KHONG tao gi tren production
//
// Day la may THAT, co khach that. Nen:
//   · `GET` cac cua doc duoc;
//   · cua GHI (`POST /duyet`, `POST /ket-noi`) do bang **su TON TAI tren bang
//     dinh tuyen**, ⛔ khong bang cach goi that. Mot `POST` that se tao ban ghi
//     hoac dong mot waitpoint cua khach.
//   · ⭐ Cach do mot cua POST ma ⛔ khong goi no: gui `POST` **thieu CSRF** va doi
//     `400`/`403`. `404` nghia la route ⛔ khong ton tai; `400` nghia la route CO
//     va no da tu choi truoc khi lam gi. Phan biet duoc hai thu do **chinh la**
//     bai hoc `404`-cua-router vs `404`-cua-`_cua_toi` hom nay.
//
//     python tools\chay_web_that.py tests\browser\agent_ui_v2_nghiem_thu_sau_deploy.js --phien saudeploy
async page => {
  const COOKIE = '__LTT_COOKIE__';
  if (!COOKIE || COOKIE.startsWith('__LTT_'))
    throw new Error('chua dien cookie — chay qua `python tools/chay_web_that.py`');

  const GOC = 'https://app.lttstudios.com';
  const loi = [], loiTrang = [], req5xx = [];
  const check = (dk, msg) => { if (!dk) loi.push(msg) };
  const so = {};

  page.on('pageerror', e => loiTrang.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error') loiTrang.push('console: ' + m.text()) });
  page.on('response', r => { if (r.status() >= 500) req5xx.push(`${r.status()} ${r.url()}`) });

  await page.context().addCookies([{
    name: 'session', value: COOKIE, domain: 'app.lttstudios.com', path: '/',
    httpOnly: true, secure: true }]);
  await page.setViewportSize({ width: 1440, height: 900 });

  // ── 0. SHA dang chay — moi so duoi day thuoc ve SHA nay ──────────────────
  await page.goto(`${GOC}/health/version`, { waitUntil: 'domcontentloaded' });
  so.sha = (await page.evaluate(() => document.body.innerText)).trim().slice(0, 200);

  const goi = (duong, tuy) => page.evaluate(async ([d, t]) => {
    const r = await fetch(d, { credentials: 'same-origin', ...(t || {}) });
    let than = null;
    try { than = await r.json() } catch { than = null }
    return { status: r.status, than };
  }, [duong, tuy]);

  // ── 1. UI-5: bon cua `/ket-noi` ──────────────────────────────────────────
  const ncc = await goi('/agent/api/v3/ket-noi/nha-cung-cap');
  so.nha_cung_cap = ncc.status;
  check(ncc.status === 200, `GET /ket-noi/nha-cung-cap -> ${ncc.status}`);
  so.so_nha_cung_cap = Array.isArray(ncc.than?.items) ? ncc.than.items.length
    : (Array.isArray(ncc.than) ? ncc.than.length : null);

  const ds = await goi('/agent/api/v3/ket-noi');
  so.ket_noi_list = ds.status;
  check(ds.status === 200, `GET /ket-noi -> ${ds.status}`);
  // ⭐ Cua nay ⛔ KHONG BAO GIO duoc tra gia tri bi mat. Do bang cach quet CA than.
  const thoBiMat = JSON.stringify(ds.than || {});
  so.than_co_khoa_bi_mat = /"bi_mat"|"secret"|"gia_tri"|sk-live/.test(thoBiMat);
  check(!so.than_co_khoa_bi_mat,
    `than /ket-noi chua khoa nghi la bi mat: ${thoBiMat.slice(0, 200)}`);

  // Cua GHI: do su TON TAI, ⛔ khong goi that. Thieu CSRF ⇒ 400/403, ⛔ khong 404.
  const tao = await goi('/agent/api/v3/ket-noi',
    { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}) });
  so.post_ket_noi = tao.status;
  check(tao.status !== 404,
    `POST /ket-noi tra 404 ⇒ route KHONG ton tai tren ban deploy`);
  check([400, 403, 422].includes(tao.status),
    `POST /ket-noi thieu CSRF phai bi tu choi, nhan ${tao.status}`);

  const xoa = await goi('/agent/api/v3/ket-noi/khong-ton-tai-0000',
    { method: 'DELETE' });
  so.delete_ket_noi = xoa.status;
  check(xoa.status !== 405,
    `DELETE /ket-noi/{id} tra 405 ⇒ phuong thuc chua duoc dang ky`);

  // ── 2. UI-8a: cua duyet ──────────────────────────────────────────────────
  const duyet = await goi(
    '/agent/api/v3/runs/00000000-0000-0000-0000-000000000000/nodes/h/duyet',
    { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}) });
  so.post_duyet = duyet.status;
  so.duyet_detail = JSON.stringify(duyet.than || {}).slice(0, 160);
  check(duyet.status !== 404 || so.duyet_detail.includes('Not Found') === false,
    `POST .../duyet -> ${duyet.status} ${so.duyet_detail}`);
  // ⭐ Phan biet 404-cua-ROUTER voi 404-cua-`_cua_toi`: router noi "Not Found".
  check(!(duyet.status === 404 && /"detail":"Not Found"/.test(so.duyet_detail)),
    'POST .../duyet: 404 den tu ROUTER ⇒ route CHUA len production');

  // ⚠️ DON `loiTrang` TRUOC khi sang pha trang. Ba muc `400`/`404` vua roi la
  //    console error do CHINH cac phep tham do o tren gay ra (toi co y `POST`
  //    thieu CSRF de do su TON TAI cua route). Neu khong don, bo do tu to cao
  //    minh, va bao cao se chua ba "loi trang" ⛔ khong thuoc ve san pham.
  // ⭐ Mot bo do phai tru chinh dau vet cua no ra khoi so lieu.
  so.console_tu_tham_do = loiTrang.length;
  loiTrang.length = 0;

  // ── 3. UI-9: trang mau ───────────────────────────────────────────────────
  const rMau = await page.goto(`${GOC}/agent/templates`,
    { waitUntil: 'load', timeout: 60000 });
  so.templates_status = rMau?.status();
  check(so.templates_status === 200, `/agent/templates -> ${so.templates_status}`);
  // 🔴 HAI loi do luong cua chinh toi o lan chay dau, ca hai cho ra BAO DONG GIA:
  //
  // 1. Toi quet `[data-mau-slug]` — mot thuoc tinh toi **TU BIA**. Thuoc tinh
  //    that la `data-mau-dung`. Ket qua `0` nghia la "toi do sai ten", ⛔ khong
  //    phai "trang khong co nut nao".
  // 2. Toi quet `/đang xây/` tren **CA body**, ma thanh dieu huong ben tren
  //    dang hien badge *"Đang xây"* cho BON muc KHAC (Lượt chạy, Các kết nối,
  //    Agent, Cài đặt). Nen no luon khop, ke ca khi trang nay da that.
  //    ⇒ Quet trong `<main>`, ⛔ khong quet ca trang.
  const mau = await page.evaluate(() => {
    const than = document.querySelector('main') ?? document.body;
    return {
      so_nut_dung: document.querySelectorAll('[data-mau-dung]').length,
      so_mau_id: document.querySelectorAll('[data-mau-id]').length,
      con_dat_cho: /đang xây|chưa được dựng/i.test(than.innerText),
      chu: than.innerText.slice(0, 200),
    };
  });
  Object.assign(so, mau);
  check(!mau.con_dat_cho, 'trang /agent/templates VAN la trang dat cho');
  check(mau.so_nut_dung >= 1,
    `khong thay nut dung mau nao (data-mau-dung = ${mau.so_nut_dung})`);

  // ── 4. Toc do Canvas: byte THAT truyen qua day ──────────────────────────
  const truyen = [];
  const dem = r => {
    const u = r.url();
    if (!/\/static\/agent-canvas\/assets\//.test(u)) return;
    truyen.push(r);
  };
  page.on('response', dem);
  const t0 = Date.now();
  await page.goto(`${GOC}/agent/canvas`, { waitUntil: 'load', timeout: 90000 });
  await page.waitForSelector('[data-testid="flow-store-status"]', { timeout: 60000 });
  so.canvas_ms_tai_xong = Date.now() - t0;
  page.off('response', dem);

  so.asset = [];
  for (const r of truyen) {
    let n = null;
    try { n = (await r.body()).length } catch { n = null }
    so.asset.push({
      ten: r.url().split('/').pop(),
      // ⭐ `content-length` la byte THAT tren day (da nen). `body()` giai nen roi,
      //    nen hai so nay KHAC nhau va ⛔ khong duoc lan.
      tren_day: Number(r.headers()['content-length']) || null,
      sau_giai_nen: n,
      nen: r.headers()['content-encoding'] || '(khong nen)',
    });
  }
  const js = so.asset.find(a => a.ten.endsWith('.js'));
  so.js_tren_day = js?.tren_day ?? null;
  check(js != null, 'khong thay tep JS cua canvas trong luot tai');
  // 🔴 PHAT HIEN: Cloudflare phuc vu bang **zstd**, ⛔ KHONG gzip.
  //
  //    Tran toi nang hom nay (`TRAN_JS_NEN = 160_000`) do **gzip** — mot con so
  //    ⛔ KHONG mo ta thu khach that su tai. Va `content-length` vang mat o
  //    phan hoi zstd streaming, nen ca phep do "byte tren day" cua toi cung
  //    khong lay duoc so.
  // ⇒ Ghi ca hai con so doc duoc, va ⛔ KHONG phan quyet tran o day: mot tran do
  //   sai dai luong thi phai sua o `test_95`, ⛔ khong sua bang mot nguong thu hai
  //   doan o kich ban nay. Muc nay ghi vao so tien do de UI-10 xu.
  so.canh_bao_nen = js?.nen && js.nen !== 'gzip'
    ? `phuc vu bang ${js.nen}, trong khi tran o test_95 do GZIP`
    : null;

  check(loiTrang.length === 0, 'loi trang: ' + JSON.stringify(loiTrang.slice(0, 4)));
  check(req5xx.length === 0, '5xx: ' + JSON.stringify(req5xx.slice(0, 4)));

  return loi.length ? { status: 'FAIL', loi, so } : { status: 'PASS', so };
}
